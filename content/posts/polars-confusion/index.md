---
title: Polars confusion
date: '2024-07-13'
categories:
  - tutorial
  - data science
  - dataframes
tags:
  - tutorial
  - python
  - polars
  - data science
  - classifier
  - confusion
  - optimization
draft: false
---


<script src="https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js" integrity="sha512-c3Nl8+7g4LMSTdrm621y7kf9v3SDPnhxLNhcjFJbKECVnmZHTdo+IRO05sNLTH/D3vA6u1X32ehoLC7WFVdheg==" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.5.1/jquery.min.js" integrity="sha512-bLT0Qm9VnAYZDflyKcBaQ2gg0hSYNQrJ8RilYldYQ1FxQYoCLtUjuuRuZo+fjqhx/qtq/1itJ0C2ejDxltZVFg==" crossorigin="anonymous" data-relocate-top="true"></script>
<script type="application/javascript">define('jquery', [],function() {return window.jQuery;})</script>


{{< admonition abstract >}}

We explore how to use [polars](https://pola.rs/)' out of the box optimizations to
make parallelized computations. An interesting example is the confusion
of a classifier model and classical derived metrics like precision, recall
or the f1-score.

{{< /admonition  >}}
{{< admonition note >}}

Polars is a blazingly fast DataFrame library implemented in Rust. It just had its 1.0 (actually 1.1) release and is a production ready tool with a stable an well designed api.

{{< /admonition  >}}

## Setup

Let us first generate some dummy data, which consists of labels (`y_true`) and
model scores (`y_prob`) with values in \[0,1\]. Furthermore we generate grouping
variables `id_1` and `id_2`, which will later be used to partition our data.

``` python
import polars as pl
import polars.selectors as cs

import numpy as np

np.random.seed(314)

def generate_data(n: int) -> pl.DataFrame:
  """
  Generate a DataFrame with random classifier output.

  Parameters:
    n (int): The number of rows in the DataFrame.

  Returns:
    pl.DataFrame: The generated DataFrame.

  """
  y_true = np.random.choice([True, False], n)
  y_prob = np.random.uniform(0, 1, n)

  id_1 = np.random.choice(15, n)
  id_2 = np.random.choice(10, n)

  schema = {
    "id_1": pl.Int32,
    "id_2": pl.Int32,
    "y_true": pl.Boolean,
    "y_prob": pl.Float32,
  }

  df = pl.DataFrame(
    {
      "id_1": id_1.tolist(),
      "id_2": id_2.tolist(),
      "y_true": y_true.tolist(),
      "y_prob": y_prob.tolist(),
    },
    schema=schema,
  )

  return df

print(generate_data(10).head())
```

    shape: (5, 4)
    ┌──────┬──────┬────────┬──────────┐
    │ id_1 ┆ id_2 ┆ y_true ┆ y_prob   │
    │ ---  ┆ ---  ┆ ---    ┆ ---      │
    │ i32  ┆ i32  ┆ bool   ┆ f32      │
    ╞══════╪══════╪════════╪══════════╡
    │ 13   ┆ 2    ┆ true   ┆ 0.827355 │
    │ 6    ┆ 0    ┆ false  ┆ 0.727951 │
    │ 13   ┆ 7    ┆ false  ┆ 0.26048  │
    │ 2    ┆ 3    ┆ false  ┆ 0.911763 │
    │ 7    ┆ 2    ┆ true   ┆ 0.260757 │
    └──────┴──────┴────────┴──────────┘

## Problem description

Metrics like precision, recall or the f1-score are defined entirely in terms of the
confusion (i.e. the number true positives, false positives, true negatives and false negatives).
These in turn are defined in terms of a threshold which defines the boolean predictions, being positive
if and only if the score is greater than or equal to the threshold.

Thus we can ask ourselves: Which threshold can we use to optimize for example the f1-score ?

The most naive approach is to compute all values of the f1-score for a large enough number of thresholds
and keep theta for which the f1-score is maximal.

The next question could be: Which thresholds can we use to optimize the f1-score on certain
partitions of our data ?

We will answer both questions at once since the first question is a special case (with a one element partition).

## Working with wide dataframes

An elegant solution to the problem is to use wide dataframes.
For each theta, we generate a boolean column `y_pred(theta)` and four columns
defining the confusion with respect to that theta. Furtermore, we add
one more column with our metric in question, lets say the f1-score. In total
we get 6\*len(theta) extra columns.

Now, the whole magic of why polars is such a great choice so solve this problem
is that all expression will be calculated in parallel, and in addition, we
can easily group our dataframe by our id (grouping) variables that define the
partition.

``` python
def add_y_pred(theta: list[float]) -> dict[str, pl.Expr]:
    """
    Add columns to the DataFrame with boolean predictions for different thresholds.
    """
    return {
        f"y_pred_{i}" : pl.col("y_prob") >= theta 
          for i, theta in enumerate(theta)
    }

def add_confusion(theta: list[float]) -> dict[str, pl.Expr]:
    """
    Add columns to the DataFrame with the confusion matrix for different thresholds.
    """
    return {
        f"tp_{i}" : pl.col("y_true") & pl.col(f"y_pred_{i}")  
          for i, theta in enumerate(theta)
    } | {
        f"fp_{i}" : ~pl.col("y_true") & pl.col(f"y_pred_{i}") 
          for i, theta in enumerate(theta)
    } | {
        f"tn_{i}" : ~pl.col("y_true") & ~pl.col(f"y_pred_{i}") 
          for i, theta in enumerate(theta)
    } | {
        f"fn_{i}" : pl.col("y_true")  & ~pl.col(f"y_pred_{i}") 
          for i, theta in enumerate(theta)
    }

def add_f1_score(theta: list[float]) -> dict[str, pl.Expr]:
    """
    Add columns to the DataFrame with the f1-score for different thresholds.
    Uses the confusion matrix.
    """
    return {
        f"f1_score_{i}" : 2 * pl.col(f"tp_{i}").sum() / (
            2 * pl.col(f"tp_{i}").sum() + pl.col(f"fp_{i}").sum() + pl.col(f"fn_{i}").sum()
          ) for i, theta in enumerate(theta)
    }

def select_best_theta(
  df: pl.DataFrame,
  theta: list[float],
) -> pl.DataFrame:
  """
  Select the best threshold.
  """
  df_theta = pl.DataFrame({"index" : range(len(theta)), "theta" : theta},
    schema={
      "index" : pl.UInt32, 
      "theta" : pl.Float32,
    })

  return (
    df
    .with_columns(
        theta_opt_ind = pl.concat_list(cs.starts_with("f1")).list.arg_max(),
        f1_opt = pl.concat_list(cs.starts_with("f1")).list.max(),
    )
    .join(
      df_theta,
      left_on="theta_opt_ind",
      right_on="index"
    )
    .rename({
      "theta" : "theta_opt",
    })
  )


def optimize(df: pl.DataFrame, theta: list[float], group_by: list[str]) -> pl.DataFrame:
  """
  Optimize the f1-score for different thresholds on different partitions of the data.
  """
  return (
    df.with_columns(
        **add_y_pred(theta),
    )
    .with_columns(
        **add_confusion(theta),
    )
    .group_by(group_by)
    .agg(
        **add_f1_score(theta)
    )
    .select(
        *group_by, cs.starts_with("f1")
    )
    .pipe(
      select_best_theta, theta
    )
    .select(
        *group_by, "theta_opt", "f1_opt",
    )
  )
```

{{< admonition example >}}

``` python
theta = [0.1, 0.5]
groups=["id_1"]
df=generate_data(100)

df_wide = (
    df.with_columns(
        **add_y_pred(theta),
    )
    .with_columns(
        **add_confusion(theta),
    )
)
df_grouped = (
  df_wide
  .group_by(groups)
  .agg(
    **add_f1_score(theta)
  )
)

df_opt = (
  df_grouped
  .pipe(select_best_theta, theta)
  .select(
    *groups, "theta_opt_ind", "theta_opt", "f1_opt",
  )
)

print(df_wide.head())
print(df_grouped.head())
print(df_opt.head())
```

    shape: (5, 14)
    ┌──────┬──────┬────────┬──────────┬───┬───────┬───────┬───────┬───────┐
    │ id_1 ┆ id_2 ┆ y_true ┆ y_prob   ┆ … ┆ tn_0  ┆ tn_1  ┆ fn_0  ┆ fn_1  │
    │ ---  ┆ ---  ┆ ---    ┆ ---      ┆   ┆ ---   ┆ ---   ┆ ---   ┆ ---   │
    │ i32  ┆ i32  ┆ bool   ┆ f32      ┆   ┆ bool  ┆ bool  ┆ bool  ┆ bool  │
    ╞══════╪══════╪════════╪══════════╪═══╪═══════╪═══════╪═══════╪═══════╡
    │ 5    ┆ 6    ┆ false  ┆ 0.771075 ┆ … ┆ false ┆ false ┆ false ┆ false │
    │ 13   ┆ 8    ┆ true   ┆ 0.566425 ┆ … ┆ false ┆ false ┆ false ┆ false │
    │ 0    ┆ 6    ┆ true   ┆ 0.306617 ┆ … ┆ false ┆ false ┆ false ┆ true  │
    │ 13   ┆ 7    ┆ false  ┆ 0.977795 ┆ … ┆ false ┆ false ┆ false ┆ false │
    │ 6    ┆ 0    ┆ true   ┆ 0.88869  ┆ … ┆ false ┆ false ┆ false ┆ false │
    └──────┴──────┴────────┴──────────┴───┴───────┴───────┴───────┴───────┘
    shape: (5, 3)
    ┌──────┬────────────┬────────────┐
    │ id_1 ┆ f1_score_0 ┆ f1_score_1 │
    │ ---  ┆ ---        ┆ ---        │
    │ i32  ┆ f64        ┆ f64        │
    ╞══════╪════════════╪════════════╡
    │ 8    ┆ 0.769231   ┆ 0.444444   │
    │ 7    ┆ 0.75       ┆ 0.571429   │
    │ 5    ┆ 0.2        ┆ 0.222222   │
    │ 2    ┆ 0.75       ┆ 0.75       │
    │ 6    ┆ 0.8        ┆ 0.75       │
    └──────┴────────────┴────────────┘
    shape: (5, 4)
    ┌──────┬───────────────┬───────────┬──────────┐
    │ id_1 ┆ theta_opt_ind ┆ theta_opt ┆ f1_opt   │
    │ ---  ┆ ---           ┆ ---       ┆ ---      │
    │ i32  ┆ u32           ┆ f32       ┆ f64      │
    ╞══════╪═══════════════╪═══════════╪══════════╡
    │ 8    ┆ 0             ┆ 0.1       ┆ 0.769231 │
    │ 7    ┆ 0             ┆ 0.1       ┆ 0.75     │
    │ 5    ┆ 1             ┆ 0.5       ┆ 0.222222 │
    │ 2    ┆ 0             ┆ 0.1       ┆ 0.75     │
    │ 6    ┆ 0             ┆ 0.1       ┆ 0.8      │
    └──────┴───────────────┴───────────┴──────────┘

{{< /admonition  >}}

## More data

Now, lets see if we can handle more data. Note that the output is generated on
a single core machine and hence the parallelization is not any help here, however
I think that the result is still quite impressive.
Feel free to benchmark this on your own or any other machine.
On my 8 core 16 GB machine, the following code runs in approximately one second.

``` python
import psutil
print(f"CPU: {psutil.cpu_count()}")
print(f"Memory: {psutil.virtual_memory().total / 1024 ** 2} MB")
```

    CPU: 8
    Memory: 16384.0 MB

``` python
groups=["id_1", "id_2"]
df = generate_data(1_000_000)
```

``` python
%%time
# use 100 equidistant thresholds
opt = optimize(df, np.arange(0,1, 0.01), groups)
print(opt.head(5))
```

    shape: (5, 4)
    ┌──────┬──────┬───────────┬──────────┐
    │ id_1 ┆ id_2 ┆ theta_opt ┆ f1_opt   │
    │ ---  ┆ ---  ┆ ---       ┆ ---      │
    │ i32  ┆ i32  ┆ f32       ┆ f64      │
    ╞══════╪══════╪═══════════╪══════════╡
    │ 10   ┆ 0    ┆ 0.0       ┆ 0.666067 │
    │ 1    ┆ 2    ┆ 0.0       ┆ 0.669303 │
    │ 8    ┆ 1    ┆ 0.0       ┆ 0.665785 │
    │ 8    ┆ 7    ┆ 0.0       ┆ 0.671941 │
    │ 5    ┆ 8    ┆ 0.0       ┆ 0.668914 │
    └──────┴──────┴───────────┴──────────┘
    CPU times: user 6.35 s, sys: 146 ms, total: 6.5 s
    Wall time: 1.08 s

``` python
import hvplot
hvplot.extension("matplotlib")

(
  opt
  .with_columns(f1_opt=pl.col("f1_opt").round(2))
  .plot
  .heatmap("id_1", "id_2", "f1_opt", height=600, width=800)
)
```

<script type="application/javascript">
(function(root) {
  function now() {
    return new Date();
  }

  var force = true;
  var py_version = '3.4.1'.replace('rc', '-rc.').replace('.dev', '-dev.');
  var reloading = false;
  var Bokeh = root.Bokeh;

  if (typeof (root._bokeh_timeout) === "undefined" || force) {
    root._bokeh_timeout = Date.now() + 5000;
    root._bokeh_failed_load = false;
  }

  function run_callbacks() {
    try {
      root._bokeh_onload_callbacks.forEach(function(callback) {
        if (callback != null)
          callback();
      });
    } finally {
      delete root._bokeh_onload_callbacks;
    }
    console.debug("Bokeh: all callbacks have finished");
  }

  function load_libs(css_urls, js_urls, js_modules, js_exports, callback) {
    if (css_urls == null) css_urls = [];
    if (js_urls == null) js_urls = [];
    if (js_modules == null) js_modules = [];
    if (js_exports == null) js_exports = {};

    root._bokeh_onload_callbacks.push(callback);

    if (root._bokeh_is_loading > 0) {
      console.debug("Bokeh: BokehJS is being loaded, scheduling callback at", now());
      return null;
    }
    if (js_urls.length === 0 && js_modules.length === 0 && Object.keys(js_exports).length === 0) {
      run_callbacks();
      return null;
    }
    if (!reloading) {
      console.debug("Bokeh: BokehJS not loaded, scheduling load and callback at", now());
    }

    function on_load() {
      root._bokeh_is_loading--;
      if (root._bokeh_is_loading === 0) {
        console.debug("Bokeh: all BokehJS libraries/stylesheets loaded");
        run_callbacks()
      }
    }
    window._bokeh_on_load = on_load

    function on_error() {
      console.error("failed to load " + url);
    }

    var skip = [];
    if (window.requirejs) {
      window.requirejs.config({'packages': {}, 'paths': {}, 'shim': {}});
      root._bokeh_is_loading = css_urls.length + 0;
    } else {
      root._bokeh_is_loading = css_urls.length + js_urls.length + js_modules.length + Object.keys(js_exports).length;
    }

    var existing_stylesheets = []
    var links = document.getElementsByTagName('link')
    for (var i = 0; i < links.length; i++) {
      var link = links[i]
      if (link.href != null) {
    existing_stylesheets.push(link.href)
      }
    }
    for (var i = 0; i < css_urls.length; i++) {
      var url = css_urls[i];
      if (existing_stylesheets.indexOf(url) !== -1) {
    on_load()
    continue;
      }
      const element = document.createElement("link");
      element.onload = on_load;
      element.onerror = on_error;
      element.rel = "stylesheet";
      element.type = "text/css";
      element.href = url;
      console.debug("Bokeh: injecting link tag for BokehJS stylesheet: ", url);
      document.body.appendChild(element);
    }    var existing_scripts = []
    var scripts = document.getElementsByTagName('script')
    for (var i = 0; i < scripts.length; i++) {
      var script = scripts[i]
      if (script.src != null) {
    existing_scripts.push(script.src)
      }
    }
    for (var i = 0; i < js_urls.length; i++) {
      var url = js_urls[i];
      if (skip.indexOf(url) !== -1 || existing_scripts.indexOf(url) !== -1) {
    if (!window.requirejs) {
      on_load();
    }
    continue;
      }
      var element = document.createElement('script');
      element.onload = on_load;
      element.onerror = on_error;
      element.async = false;
      element.src = url;
      console.debug("Bokeh: injecting script tag for BokehJS library: ", url);
      document.head.appendChild(element);
    }
    for (var i = 0; i < js_modules.length; i++) {
      var url = js_modules[i];
      if (skip.indexOf(url) !== -1 || existing_scripts.indexOf(url) !== -1) {
    if (!window.requirejs) {
      on_load();
    }
    continue;
      }
      var element = document.createElement('script');
      element.onload = on_load;
      element.onerror = on_error;
      element.async = false;
      element.src = url;
      element.type = "module";
      console.debug("Bokeh: injecting script tag for BokehJS library: ", url);
      document.head.appendChild(element);
    }
    for (const name in js_exports) {
      var url = js_exports[name];
      if (skip.indexOf(url) >= 0 || root[name] != null) {
    if (!window.requirejs) {
      on_load();
    }
    continue;
      }
      var element = document.createElement('script');
      element.onerror = on_error;
      element.async = false;
      element.type = "module";
      console.debug("Bokeh: injecting script tag for BokehJS library: ", url);
      element.textContent = `
      import ${name} from "${url}"
      window.${name} = ${name}
      window._bokeh_on_load()
      `
      document.head.appendChild(element);
    }
    if (!js_urls.length && !js_modules.length) {
      on_load()
    }
  };

  function inject_raw_css(css) {
    const element = document.createElement("style");
    element.appendChild(document.createTextNode(css));
    document.body.appendChild(element);
  }

  var js_urls = ["https://cdn.bokeh.org/bokeh/release/bokeh-3.4.1.min.js", "https://cdn.bokeh.org/bokeh/release/bokeh-gl-3.4.1.min.js", "https://cdn.bokeh.org/bokeh/release/bokeh-widgets-3.4.1.min.js", "https://cdn.bokeh.org/bokeh/release/bokeh-tables-3.4.1.min.js", "https://cdn.holoviz.org/panel/1.4.2/dist/panel.min.js"];
  var js_modules = [];
  var js_exports = {};
  var css_urls = [];
  var inline_js = [    function(Bokeh) {
      Bokeh.set_log_level("info");
    },
function(Bokeh) {} // ensure no trailing comma for IE
  ];

  function run_inline_js() {
    if ((root.Bokeh !== undefined) || (force === true)) {
      for (var i = 0; i < inline_js.length; i++) {
    try {
          inline_js[i].call(root, root.Bokeh);
    } catch(e) {
      if (!reloading) {
        throw e;
      }
    }
      }
      // Cache old bokeh versions
      if (Bokeh != undefined && !reloading) {
    var NewBokeh = root.Bokeh;
    if (Bokeh.versions === undefined) {
      Bokeh.versions = new Map();
    }
    if (NewBokeh.version !== Bokeh.version) {
      Bokeh.versions.set(NewBokeh.version, NewBokeh)
    }
    root.Bokeh = Bokeh;
      }} else if (Date.now() < root._bokeh_timeout) {
      setTimeout(run_inline_js, 100);
    } else if (!root._bokeh_failed_load) {
      console.log("Bokeh: BokehJS failed to load within specified timeout.");
      root._bokeh_failed_load = true;
    }
    root._bokeh_is_initializing = false
  }

  function load_or_wait() {
    // Implement a backoff loop that tries to ensure we do not load multiple
    // versions of Bokeh and its dependencies at the same time.
    // In recent versions we use the root._bokeh_is_initializing flag
    // to determine whether there is an ongoing attempt to initialize
    // bokeh, however for backward compatibility we also try to ensure
    // that we do not start loading a newer (Panel>=1.0 and Bokeh>3) version
    // before older versions are fully initialized.
    if (root._bokeh_is_initializing && Date.now() > root._bokeh_timeout) {
      root._bokeh_is_initializing = false;
      root._bokeh_onload_callbacks = undefined;
      console.log("Bokeh: BokehJS was loaded multiple times but one version failed to initialize.");
      load_or_wait();
    } else if (root._bokeh_is_initializing || (typeof root._bokeh_is_initializing === "undefined" && root._bokeh_onload_callbacks !== undefined)) {
      setTimeout(load_or_wait, 100);
    } else {
      root._bokeh_is_initializing = true
      root._bokeh_onload_callbacks = []
      var bokeh_loaded = Bokeh != null && (Bokeh.version === py_version || (Bokeh.versions !== undefined && Bokeh.versions.has(py_version)));
      if (!reloading && !bokeh_loaded) {
    root.Bokeh = undefined;
      }
      load_libs(css_urls, js_urls, js_modules, js_exports, function() {
    console.debug("Bokeh: BokehJS plotting callback run at", now());
    run_inline_js();
      });
    }
  }
  // Give older versions of the autoload script a head-start to ensure
  // they initialize before we start loading newer version.
  setTimeout(load_or_wait, 100)
}(window));
</script>
<script type="application/javascript">

if ((window.PyViz === undefined) || (window.PyViz instanceof HTMLElement)) {
  window.PyViz = {comms: {}, comm_status:{}, kernels:{}, receivers: {}, plot_index: []}
}


    function JupyterCommManager() {
    }

    JupyterCommManager.prototype.register_target = function(plot_id, comm_id, msg_handler) {
      if (window.comm_manager || ((window.Jupyter !== undefined) && (Jupyter.notebook.kernel != null))) {
        var comm_manager = window.comm_manager || Jupyter.notebook.kernel.comm_manager;
        comm_manager.register_target(comm_id, function(comm) {
          comm.on_msg(msg_handler);
        });
      } else if ((plot_id in window.PyViz.kernels) && (window.PyViz.kernels[plot_id])) {
        window.PyViz.kernels[plot_id].registerCommTarget(comm_id, function(comm) {
          comm.onMsg = msg_handler;
        });
      } else if (typeof google != 'undefined' && google.colab.kernel != null) {
        google.colab.kernel.comms.registerTarget(comm_id, (comm) => {
          var messages = comm.messages[Symbol.asyncIterator]();
          function processIteratorResult(result) {
            var message = result.value;
            console.log(message)
            var content = {data: message.data, comm_id};
            var buffers = []
            for (var buffer of message.buffers || []) {
              buffers.push(new DataView(buffer))
            }
            var metadata = message.metadata || {};
            var msg = {content, buffers, metadata}
            msg_handler(msg);
            return messages.next().then(processIteratorResult);
          }
          return messages.next().then(processIteratorResult);
        })
      }
    }

    JupyterCommManager.prototype.get_client_comm = function(plot_id, comm_id, msg_handler) {
      if (comm_id in window.PyViz.comms) {
        return window.PyViz.comms[comm_id];
      } else if (window.comm_manager || ((window.Jupyter !== undefined) && (Jupyter.notebook.kernel != null))) {
        var comm_manager = window.comm_manager || Jupyter.notebook.kernel.comm_manager;
        var comm = comm_manager.new_comm(comm_id, {}, {}, {}, comm_id);
        if (msg_handler) {
          comm.on_msg(msg_handler);
        }
      } else if ((plot_id in window.PyViz.kernels) && (window.PyViz.kernels[plot_id])) {
        var comm = window.PyViz.kernels[plot_id].connectToComm(comm_id);
        comm.open();
        if (msg_handler) {
          comm.onMsg = msg_handler;
        }
      } else if (typeof google != 'undefined' && google.colab.kernel != null) {
        var comm_promise = google.colab.kernel.comms.open(comm_id)
        comm_promise.then((comm) => {
          window.PyViz.comms[comm_id] = comm;
          if (msg_handler) {
            var messages = comm.messages[Symbol.asyncIterator]();
            function processIteratorResult(result) {
              var message = result.value;
              var content = {data: message.data};
              var metadata = message.metadata || {comm_id};
              var msg = {content, metadata}
              msg_handler(msg);
              return messages.next().then(processIteratorResult);
            }
            return messages.next().then(processIteratorResult);
          }
        }) 
        var sendClosure = (data, metadata, buffers, disposeOnDone) => {
          return comm_promise.then((comm) => {
            comm.send(data, metadata, buffers, disposeOnDone);
          });
        };
        var comm = {
          send: sendClosure
        };
      }
      window.PyViz.comms[comm_id] = comm;
      return comm;
    }
    window.PyViz.comm_manager = new JupyterCommManager();
    


var JS_MIME_TYPE = 'application/javascript';
var HTML_MIME_TYPE = 'text/html';
var EXEC_MIME_TYPE = 'application/vnd.holoviews_exec.v0+json';
var CLASS_NAME = 'output';

/**
 * Render data to the DOM node
 */
function render(props, node) {
  var div = document.createElement("div");
  var script = document.createElement("script");
  node.appendChild(div);
  node.appendChild(script);
}

/**
 * Handle when a new output is added
 */
function handle_add_output(event, handle) {
  var output_area = handle.output_area;
  var output = handle.output;
  if ((output.data == undefined) || (!output.data.hasOwnProperty(EXEC_MIME_TYPE))) {
    return
  }
  var id = output.metadata[EXEC_MIME_TYPE]["id"];
  var toinsert = output_area.element.find("." + CLASS_NAME.split(' ')[0]);
  if (id !== undefined) {
    var nchildren = toinsert.length;
    var html_node = toinsert[nchildren-1].children[0];
    html_node.innerHTML = output.data[HTML_MIME_TYPE];
    var scripts = [];
    var nodelist = html_node.querySelectorAll("script");
    for (var i in nodelist) {
      if (nodelist.hasOwnProperty(i)) {
        scripts.push(nodelist[i])
      }
    }

    scripts.forEach( function (oldScript) {
      var newScript = document.createElement("script");
      var attrs = [];
      var nodemap = oldScript.attributes;
      for (var j in nodemap) {
        if (nodemap.hasOwnProperty(j)) {
          attrs.push(nodemap[j])
        }
      }
      attrs.forEach(function(attr) { newScript.setAttribute(attr.name, attr.value) });
      newScript.appendChild(document.createTextNode(oldScript.innerHTML));
      oldScript.parentNode.replaceChild(newScript, oldScript);
    });
    if (JS_MIME_TYPE in output.data) {
      toinsert[nchildren-1].children[1].textContent = output.data[JS_MIME_TYPE];
    }
    output_area._hv_plot_id = id;
    if ((window.Bokeh !== undefined) && (id in Bokeh.index)) {
      window.PyViz.plot_index[id] = Bokeh.index[id];
    } else {
      window.PyViz.plot_index[id] = null;
    }
  } else if (output.metadata[EXEC_MIME_TYPE]["server_id"] !== undefined) {
    var bk_div = document.createElement("div");
    bk_div.innerHTML = output.data[HTML_MIME_TYPE];
    var script_attrs = bk_div.children[0].attributes;
    for (var i = 0; i < script_attrs.length; i++) {
      toinsert[toinsert.length - 1].childNodes[1].setAttribute(script_attrs[i].name, script_attrs[i].value);
    }
    // store reference to server id on output_area
    output_area._bokeh_server_id = output.metadata[EXEC_MIME_TYPE]["server_id"];
  }
}

/**
 * Handle when an output is cleared or removed
 */
function handle_clear_output(event, handle) {
  var id = handle.cell.output_area._hv_plot_id;
  var server_id = handle.cell.output_area._bokeh_server_id;
  if (((id === undefined) || !(id in PyViz.plot_index)) && (server_id !== undefined)) { return; }
  var comm = window.PyViz.comm_manager.get_client_comm("hv-extension-comm", "hv-extension-comm", function () {});
  if (server_id !== null) {
    comm.send({event_type: 'server_delete', 'id': server_id});
    return;
  } else if (comm !== null) {
    comm.send({event_type: 'delete', 'id': id});
  }
  delete PyViz.plot_index[id];
  if ((window.Bokeh !== undefined) & (id in window.Bokeh.index)) {
    var doc = window.Bokeh.index[id].model.document
    doc.clear();
    const i = window.Bokeh.documents.indexOf(doc);
    if (i > -1) {
      window.Bokeh.documents.splice(i, 1);
    }
  }
}

/**
 * Handle kernel restart event
 */
function handle_kernel_cleanup(event, handle) {
  delete PyViz.comms["hv-extension-comm"];
  window.PyViz.plot_index = {}
}

/**
 * Handle update_display_data messages
 */
function handle_update_output(event, handle) {
  handle_clear_output(event, {cell: {output_area: handle.output_area}})
  handle_add_output(event, handle)
}

function register_renderer(events, OutputArea) {
  function append_mime(data, metadata, element) {
    // create a DOM node to render to
    var toinsert = this.create_output_subarea(
    metadata,
    CLASS_NAME,
    EXEC_MIME_TYPE
    );
    this.keyboard_manager.register_events(toinsert);
    // Render to node
    var props = {data: data, metadata: metadata[EXEC_MIME_TYPE]};
    render(props, toinsert[0]);
    element.append(toinsert);
    return toinsert
  }

  events.on('output_added.OutputArea', handle_add_output);
  events.on('output_updated.OutputArea', handle_update_output);
  events.on('clear_output.CodeCell', handle_clear_output);
  events.on('delete.Cell', handle_clear_output);
  events.on('kernel_ready.Kernel', handle_kernel_cleanup);

  OutputArea.prototype.register_mime_type(EXEC_MIME_TYPE, append_mime, {
    safe: true,
    index: 0
  });
}

if (window.Jupyter !== undefined) {
  try {
    var events = require('base/js/events');
    var OutputArea = require('notebook/js/outputarea').OutputArea;
    if (OutputArea.prototype.mime_types().indexOf(EXEC_MIME_TYPE) == -1) {
      register_renderer(events, OutputArea);
    }
  } catch(err) {
  }
}

</script>
<style>*[data-root-id],
*[data-root-id] > * {
  box-sizing: border-box;
  font-family: var(--jp-ui-font-family);
  font-size: var(--jp-ui-font-size1);
  color: var(--vscode-editor-foreground, var(--jp-ui-font-color1));
}

/* Override VSCode background color */
.cell-output-ipywidget-background:has(
    > .cell-output-ipywidget-background > .lm-Widget > *[data-root-id]
  ),
.cell-output-ipywidget-background:has(> .lm-Widget > *[data-root-id]) {
  background-color: transparent !important;
}
</style>
<div id='p1054'>
  <div id="d560f874-da0b-4fe9-86f7-66a2525a8f98" data-root-id="p1054" style="display: contents;"></div>
</div>
<script type="application/javascript">(function(root) {
  var docs_json = {"c0a04397-6486-472f-9f7e-736a171f21b0":{"version":"3.4.1","title":"Bokeh Application","roots":[{"type":"object","name":"panel.models.browser.BrowserInfo","id":"p1054"},{"type":"object","name":"panel.models.comm_manager.CommManager","id":"p1055","attributes":{"plot_id":"p1054","comm_id":"9ec7f94c441e4531b5d05d0f02641aed","client_comm_id":"f09f001f9b3a4f84a10a3691489956b1"}}],"defs":[{"type":"model","name":"ReactiveHTML1"},{"type":"model","name":"FlexBox1","properties":[{"name":"align_content","kind":"Any","default":"flex-start"},{"name":"align_items","kind":"Any","default":"flex-start"},{"name":"flex_direction","kind":"Any","default":"row"},{"name":"flex_wrap","kind":"Any","default":"wrap"},{"name":"gap","kind":"Any","default":""},{"name":"justify_content","kind":"Any","default":"flex-start"}]},{"type":"model","name":"FloatPanel1","properties":[{"name":"config","kind":"Any","default":{"type":"map"}},{"name":"contained","kind":"Any","default":true},{"name":"position","kind":"Any","default":"right-top"},{"name":"offsetx","kind":"Any","default":null},{"name":"offsety","kind":"Any","default":null},{"name":"theme","kind":"Any","default":"primary"},{"name":"status","kind":"Any","default":"normalized"}]},{"type":"model","name":"GridStack1","properties":[{"name":"mode","kind":"Any","default":"warn"},{"name":"ncols","kind":"Any","default":null},{"name":"nrows","kind":"Any","default":null},{"name":"allow_resize","kind":"Any","default":true},{"name":"allow_drag","kind":"Any","default":true},{"name":"state","kind":"Any","default":[]}]},{"type":"model","name":"drag1","properties":[{"name":"slider_width","kind":"Any","default":5},{"name":"slider_color","kind":"Any","default":"black"},{"name":"value","kind":"Any","default":50}]},{"type":"model","name":"click1","properties":[{"name":"terminal_output","kind":"Any","default":""},{"name":"debug_name","kind":"Any","default":""},{"name":"clears","kind":"Any","default":0}]},{"type":"model","name":"FastWrapper1","properties":[{"name":"object","kind":"Any","default":null},{"name":"style","kind":"Any","default":null}]},{"type":"model","name":"NotificationAreaBase1","properties":[{"name":"js_events","kind":"Any","default":{"type":"map"}},{"name":"position","kind":"Any","default":"bottom-right"},{"name":"_clear","kind":"Any","default":0}]},{"type":"model","name":"NotificationArea1","properties":[{"name":"js_events","kind":"Any","default":{"type":"map"}},{"name":"notifications","kind":"Any","default":[]},{"name":"position","kind":"Any","default":"bottom-right"},{"name":"_clear","kind":"Any","default":0},{"name":"types","kind":"Any","default":[{"type":"map","entries":[["type","warning"],["background","#ffc107"],["icon",{"type":"map","entries":[["className","fas fa-exclamation-triangle"],["tagName","i"],["color","white"]]}]]},{"type":"map","entries":[["type","info"],["background","#007bff"],["icon",{"type":"map","entries":[["className","fas fa-info-circle"],["tagName","i"],["color","white"]]}]]}]}]},{"type":"model","name":"Notification","properties":[{"name":"background","kind":"Any","default":null},{"name":"duration","kind":"Any","default":3000},{"name":"icon","kind":"Any","default":null},{"name":"message","kind":"Any","default":""},{"name":"notification_type","kind":"Any","default":null},{"name":"_destroyed","kind":"Any","default":false}]},{"type":"model","name":"TemplateActions1","properties":[{"name":"open_modal","kind":"Any","default":0},{"name":"close_modal","kind":"Any","default":0}]},{"type":"model","name":"BootstrapTemplateActions1","properties":[{"name":"open_modal","kind":"Any","default":0},{"name":"close_modal","kind":"Any","default":0}]},{"type":"model","name":"TemplateEditor1","properties":[{"name":"layout","kind":"Any","default":[]}]},{"type":"model","name":"MaterialTemplateActions1","properties":[{"name":"open_modal","kind":"Any","default":0},{"name":"close_modal","kind":"Any","default":0}]},{"type":"model","name":"copy_to_clipboard1","properties":[{"name":"fill","kind":"Any","default":"none"},{"name":"value","kind":"Any","default":null}]}]}};
  var render_items = [{"docid":"c0a04397-6486-472f-9f7e-736a171f21b0","roots":{"p1054":"d560f874-da0b-4fe9-86f7-66a2525a8f98"},"root_ids":["p1054"]}];
  var docs = Object.values(docs_json)
  if (!docs) {
    return
  }
  const py_version = docs[0].version.replace('rc', '-rc.').replace('.dev', '-dev.')
  function embed_document(root) {
    var Bokeh = get_bokeh(root)
    Bokeh.embed.embed_items_notebook(docs_json, render_items);
    for (const render_item of render_items) {
      for (const root_id of render_item.root_ids) {
    const id_el = document.getElementById(root_id)
    if (id_el.children.length && (id_el.children[0].className === 'bk-root')) {
      const root_el = id_el.children[0]
      root_el.id = root_el.id + '-rendered'
    }
      }
    }
  }
  function get_bokeh(root) {
    if (root.Bokeh === undefined) {
      return null
    } else if (root.Bokeh.version !== py_version) {
      if (root.Bokeh.versions === undefined || !root.Bokeh.versions.has(py_version)) {
    return null
      }
      return root.Bokeh.versions.get(py_version);
    } else if (root.Bokeh.version === py_version) {
      return root.Bokeh
    }
    return null
  }
  function is_loaded(root) {
    var Bokeh = get_bokeh(root)
    return (Bokeh != null && Bokeh.Panel !== undefined)
  }
  if (is_loaded(root)) {
    embed_document(root);
  } else {
    var attempts = 0;
    var timer = setInterval(function(root) {
      if (is_loaded(root)) {
        clearInterval(timer);
        embed_document(root);
      } else if (document.readyState == "complete") {
        attempts++;
        if (attempts > 200) {
          clearInterval(timer);
      var Bokeh = get_bokeh(root)
      if (Bokeh == null || Bokeh.Panel == null) {
            console.warn("Panel: ERROR: Unable to run Panel code because Bokeh or Panel library is missing");
      } else {
        console.warn("Panel: WARNING: Attempting to render but not all required libraries could be resolved.")
        embed_document(root)
      }
        }
      }
    }, 25, root)
  }
})(window);</script>
<img src='data:image/png;base64,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e3327Nn4/f7w81WrVh31zURERETszIzpm0dXgsEgc+fO5dVXX6WiooKlS5dGnIAD4PV6WbhwIe+88w6ffPIJDz74YHjZrFmz+PWvf82mTZtYv349mZmZ4WX33XcfGzZsYMOGDYwYMaLLHA899BCXX345u3fvZvfu3fzoRz/iv/7rv465Ly27hNG8efOYMGGCVasTERER+UZav349BQUF5OfnAzBjxgxWrFgRcWb3I488wty5c0lLSwMIF5IVFRUEAoFwTZaUlNTtHI899hjvvfceiYmJQKjW+/a3v33MF2i3rMi04iSg4I4Omu4+aEEaa6TdFh/tCBEK7n462hEi2K1/pGt2+m7Zjd22ZbuNlfpHustuYzUg4RgaGX1zDaP6+vqIM7XnzJnDnDlzAKirq2PIkCHhZdnZ2bz33nsRP19ZWQnAWWedRTAY5I477uA73/kOlZWVpKamcskll1BdXc348eO55557cDgcANx+++0sWLCACy64gHvuuYfY2NgjZjRNM/xzAA6H42vVe5YVmUYfDYqIiIhIr+mjciYjI4Py8vJu/3wgEMDr9bJmzRpqa2sZO3YsGzduJBAI8NZbb/Hhhx+Sk5PDD37wA5544gmuvvpqFi5cyODBg/H5fMyZM4dFixYxf/78I77HlVdeyejRo7n44osBePHFF7n66quPOaNO1BcRERGxEY/HQ01NTfh5bW0tHo8nok12djZTp07F5XKRl5fHsGHD8Hq9ZGdnM2LECPLz83E6nUybNo0PPvgAgKysLAzDIDY2liuvvJL169d3mePGG2/k8ccfJz09nfT0dB5//HF+9atfhZc3NTV1+fOWzWTm5uZatSoRERGRPmfa5LaSo0aNwuv1Ul1djcfjYdmyZTzzzDMRbaZNm8bSpUu58soraWhooLKykvz8fFJTU9m7dy/19fVkZGSwevXq8G75HTt2kJWVhWmavPjii5x22mlHzVJaWkppaelXLrvgggvCBexXOWqRebS7+lxyySXH1E5ERETE9mxw9J/T6eThhx9m0qRJBINBrrrqKoqLi5k/fz5lZWVMnTqVSZMm8dprr1FUVITD4eC+++5j4MCBANx///1ccMEFmKbJyJEjueaaawC4/PLLqa+vxzRNRowYwe9///se5Tza8ZlHLTJffvllAHbv3s27777L+eefD8Abb7zBmWeeGS4yRURE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5syZrFmzhoaGBgYNGsSdd97J1VdffcT2ifllFC94r7fifG1Ndx+MdgT5GtJui492hAh2237s1D926xvpX+y0LYO25/5kQMJ5R7wAOkDS8JGMeOnvfZKlbfqZXWY5HvTqTObSpUt7c/UiIiIiljm0u1ys0a+OyRQRERGR/qFfHZMpIiIi0lsMwKmZTMuoyBQRERHppN3l1tHuchERERGxnGYyRURERNDucqupyBQREREBjG/QhdL7gnaXi4iIiIjlNJMpIiIignaXW00zmSIiIiJiOc1kioiIiHRyGL12t+1vHBWZIiIiImh3udW0u1xERERELKeZTBERERFCM5m6hJF1VGSKiIiIELpOpnaXW0e7y0VERETEcprJ7ELVpsujHSFCQeHT0Y4QIe22+GhHiNB098FoR4hgt/6Zf3l7tCOELcBeffOPH18S7QgRRv1pebQjRLDbd8tu7PRvhd3+neiPtLvcOprJFBERERHLaSZTREREBF3CyGoqMkVERETQ2eVW0+5yEREREbGcZjJFREREOqkwso76UkRERATtLreadpeLiIiIiOU0kykiIiLCoTv+mNGOcdxQkSkiIiLSSbvLraPd5SIiIiJiOc1kioiIiKATf6ymmUwRERERsZxmMkVERETQbSWtpiJTREREBMDQ7nIr9bsic99HK/nsTzdidgTJOO8qsqbMO6xN43vPUbd8ARgGCTnDGXrdUwC0N3zG1sfm4GusBQyG3fwysRm5PUy0G9gImMBJwMlf0aYO2Ezob6QUYGTn6590/rwJZACndbbpvtaWVTTsugXMDlJSZ5F2wk2HtWnev5zG+rsxMHDHlTDY80cOtK6lYdet4TZ+XyWDPI+TlDyl21nsNlZ26huwX/+8v/I1HvnVLXQEg0y4+id8/9abD2vz1rMvsPTOu8EwyDv9NH799BMAXORM5qSSYgAycobwbyue61EWsF//2Om7bre+0XfraOyz7YD9xstuecQ6vV5krly5kl/+8pcEg0Fmz57NrbfeevQfOgKzI8i2J69n2LyVuNOzqZg/htTSKcR7isJt2nZ62fHyIgrnr8WZmIZ/3+7wsuo/XEHW1N8woGQCwbYWMHp6SKoJfAR8G4gH1gKDgeQvtGkBvMDZgBto73y9sfNxXufzt4E9wAndT2MGqd95E56cFThdHmqqzyUx+ULcsaeG2/h8VTQ1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XMm9997LSy+9REJCQrTj4PV6w/+/YsWKqP1uBigpKWH37t1s3bqVrVu3kp2dzQcffMDgwYOjlkmOUbTPPLLaX/7yF/Pkk0828/PzzbvuuiuqWWbMmGEOHjzYdDqdpsfjMR999NGo5nnrrbdMwCwpKTFPP/108/TTTzf/8pe/RC3PP//5T3PEiBFmSUmJWVxcbN55551Ry/JFb7zxRtTPLt+yZYs5fPhwc/jw4WZRUVHUt2XTNM0PP/zQHDlypFlSUmJedNFFZmNjY1TztLS0mOnp6ebevXujmuOQ+fPnm6eccopZXFxs/uhHPzLb2tqiluXss882CwsLzeHDh5t/+9vfopLhq37/NTQ0mOeff75ZUFBgXnDBBeaePXuilmX58uWmx+Mx3W63mZmZaU6cOLFPshwpz9ChQ83s7Ozw7+a+PJv7q/JccsklZnFxsVlSUmJ+73vfM2tra6Oa54vsduUNOTLd8UdERERELHdc7S4XEREREXtQkSkiIiIillORKSIiIiKWU5EpIiIiIpZTkSkiIiIillORKSIiIiKWU5EpIrZ05plnfuXrV1xxBc8///wRf+7hhx+moKAAwzBoaGjorXgiInIUKjJFxJa6e1vGs846i7/97W+cdNJJFicSEZGvwxntACIiXyUpKYmWlhZM0+QXv/gFq1atYsiQIbjd7i5/7owzzuijhCIi0hXNZIqIrf1//9//x+bNm6moqOB//ud/uj3DKSIifUtFpojY2tq1a5k5cyYOh4MTTzyR888/P9qRRETkGKjIFBERERHLqcgUEVsbO3Ysf/7znwkGg+zYsYM33ngj2pFEROQYqMgUEVu7+OKLOfnkkykqKmLWrFl8+9vf7rL9f/7nf5KdnU1tbS3Dhw9n9uzZfZRURES+yDBN04x2CBERERE5vmgmU0REREQsp+tkiki/dPHFF1NdXR3x2qJFi5g0aVKUEomIyBdpd7mIiIiIWE67y0VERETEcioyRURERMRyKjJFRERExHIqMkVERETEcioyRURERMRy/z8DOKT6XgHvywAAAABJRU5ErkJggg==' style='max-width:100%; margin: auto; display: block; '/>

Feel free to experiment with that code or to build a benchmark using different
techniques and tools.
