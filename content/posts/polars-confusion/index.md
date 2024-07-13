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
    .pipe(
      lambda df: df,
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
    │ 1    ┆ 0.0        ┆ 0.0        │
    │ 14   ┆ 0.615385   ┆ 0.363636   │
    │ 2    ┆ 0.75       ┆ 0.75       │
    │ 12   ┆ 0.666667   ┆ 0.0        │
    │ 10   ┆ 0.444444   ┆ 0.285714   │
    └──────┴────────────┴────────────┘
    shape: (5, 4)
    ┌──────┬───────────────┬───────────┬──────────┐
    │ id_1 ┆ theta_opt_ind ┆ theta_opt ┆ f1_opt   │
    │ ---  ┆ ---           ┆ ---       ┆ ---      │
    │ i32  ┆ u32           ┆ f32       ┆ f64      │
    ╞══════╪═══════════════╪═══════════╪══════════╡
    │ 1    ┆ 0             ┆ 0.1       ┆ 0.0      │
    │ 14   ┆ 0             ┆ 0.1       ┆ 0.615385 │
    │ 2    ┆ 0             ┆ 0.1       ┆ 0.75     │
    │ 12   ┆ 0             ┆ 0.1       ┆ 0.666667 │
    │ 10   ┆ 0             ┆ 0.1       ┆ 0.444444 │
    └──────┴───────────────┴───────────┴──────────┘

{{< /admonition  >}}

## More data

Now, lets see if we can handle more data. Note that the output is generated on
a single core machine. On my 8 core 16 GB machine, the following code runs in
approximately 14 seconds.

``` python
import psutil
print(f"CPU: {psutil.cpu_count()}")
print(f"Memory: {psutil.virtual_memory().total / 1024 ** 2} MB")
```

    CPU: 8
    Memory: 16384.0 MB

``` python
groups=["id_1", "id_2"]
df = generate_data(10_000_000)
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
    │ 5    ┆ 1    ┆ 0.0       ┆ 0.666754 │
    │ 10   ┆ 9    ┆ 0.0       ┆ 0.66843  │
    │ 10   ┆ 4    ┆ 0.0       ┆ 0.66746  │
    │ 14   ┆ 0    ┆ 0.0       ┆ 0.667492 │
    │ 10   ┆ 8    ┆ 0.0       ┆ 0.665119 │
    └──────┴──────┴───────────┴──────────┘
    CPU times: user 1min 6s, sys: 12.4 s, total: 1min 19s
    Wall time: 14 s

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
<div id='p1036'>
  <div id="b0d1621a-90f7-4f92-8bf8-c46399f620ee" data-root-id="p1036" style="display: contents;"></div>
</div>
<script type="application/javascript">(function(root) {
  var docs_json = {"3f3005a3-1dd7-4eb3-9f00-462e32bc557b":{"version":"3.4.1","title":"Bokeh Application","roots":[{"type":"object","name":"panel.models.browser.BrowserInfo","id":"p1036"},{"type":"object","name":"panel.models.comm_manager.CommManager","id":"p1037","attributes":{"plot_id":"p1036","comm_id":"b3c20ac1c5f844778cefe9080f847cab","client_comm_id":"ea52afab75434e71b708dcf49bfbb52f"}}],"defs":[{"type":"model","name":"ReactiveHTML1"},{"type":"model","name":"FlexBox1","properties":[{"name":"align_content","kind":"Any","default":"flex-start"},{"name":"align_items","kind":"Any","default":"flex-start"},{"name":"flex_direction","kind":"Any","default":"row"},{"name":"flex_wrap","kind":"Any","default":"wrap"},{"name":"gap","kind":"Any","default":""},{"name":"justify_content","kind":"Any","default":"flex-start"}]},{"type":"model","name":"FloatPanel1","properties":[{"name":"config","kind":"Any","default":{"type":"map"}},{"name":"contained","kind":"Any","default":true},{"name":"position","kind":"Any","default":"right-top"},{"name":"offsetx","kind":"Any","default":null},{"name":"offsety","kind":"Any","default":null},{"name":"theme","kind":"Any","default":"primary"},{"name":"status","kind":"Any","default":"normalized"}]},{"type":"model","name":"GridStack1","properties":[{"name":"mode","kind":"Any","default":"warn"},{"name":"ncols","kind":"Any","default":null},{"name":"nrows","kind":"Any","default":null},{"name":"allow_resize","kind":"Any","default":true},{"name":"allow_drag","kind":"Any","default":true},{"name":"state","kind":"Any","default":[]}]},{"type":"model","name":"drag1","properties":[{"name":"slider_width","kind":"Any","default":5},{"name":"slider_color","kind":"Any","default":"black"},{"name":"value","kind":"Any","default":50}]},{"type":"model","name":"click1","properties":[{"name":"terminal_output","kind":"Any","default":""},{"name":"debug_name","kind":"Any","default":""},{"name":"clears","kind":"Any","default":0}]},{"type":"model","name":"FastWrapper1","properties":[{"name":"object","kind":"Any","default":null},{"name":"style","kind":"Any","default":null}]},{"type":"model","name":"NotificationAreaBase1","properties":[{"name":"js_events","kind":"Any","default":{"type":"map"}},{"name":"position","kind":"Any","default":"bottom-right"},{"name":"_clear","kind":"Any","default":0}]},{"type":"model","name":"NotificationArea1","properties":[{"name":"js_events","kind":"Any","default":{"type":"map"}},{"name":"notifications","kind":"Any","default":[]},{"name":"position","kind":"Any","default":"bottom-right"},{"name":"_clear","kind":"Any","default":0},{"name":"types","kind":"Any","default":[{"type":"map","entries":[["type","warning"],["background","#ffc107"],["icon",{"type":"map","entries":[["className","fas fa-exclamation-triangle"],["tagName","i"],["color","white"]]}]]},{"type":"map","entries":[["type","info"],["background","#007bff"],["icon",{"type":"map","entries":[["className","fas fa-info-circle"],["tagName","i"],["color","white"]]}]]}]}]},{"type":"model","name":"Notification","properties":[{"name":"background","kind":"Any","default":null},{"name":"duration","kind":"Any","default":3000},{"name":"icon","kind":"Any","default":null},{"name":"message","kind":"Any","default":""},{"name":"notification_type","kind":"Any","default":null},{"name":"_destroyed","kind":"Any","default":false}]},{"type":"model","name":"TemplateActions1","properties":[{"name":"open_modal","kind":"Any","default":0},{"name":"close_modal","kind":"Any","default":0}]},{"type":"model","name":"BootstrapTemplateActions1","properties":[{"name":"open_modal","kind":"Any","default":0},{"name":"close_modal","kind":"Any","default":0}]},{"type":"model","name":"TemplateEditor1","properties":[{"name":"layout","kind":"Any","default":[]}]},{"type":"model","name":"MaterialTemplateActions1","properties":[{"name":"open_modal","kind":"Any","default":0},{"name":"close_modal","kind":"Any","default":0}]},{"type":"model","name":"copy_to_clipboard1","properties":[{"name":"fill","kind":"Any","default":"none"},{"name":"value","kind":"Any","default":null}]}]}};
  var render_items = [{"docid":"3f3005a3-1dd7-4eb3-9f00-462e32bc557b","roots":{"p1036":"b0d1621a-90f7-4f92-8bf8-c46399f620ee"},"root_ids":["p1036"]}];
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
<img src='data:image/png;base64,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QI/JPHLkCC0tLVx22WUcOXKEjRs3smjRIj/mGAEMBbZjDp8nYV7K4DPMFTUR88yyOmAz5reYwckR0qOYW0zxfmRQns6XBSKjorj/uad5bMIttHi93DhzOgMy0nlp0RMMys4kt2ASmePz2bVxE3MzsoiIjGDm0l/SM978/FnLFvPTGydhGAZXZI1g3JyZfiayV/8oT8fstf7Yq2+UR3nCK49YyWEYhhGomX/xxRfceuutAHg8Hu6++24effTRc4dxxALXByqOhLkNLWtCHaGdmyOmhTqCXCCtOyKXhqysmg4vpdg9PpvBkz4MSpaoslw/L+tofwEdyUxJSeGjjz4K5EeIiIiIiA11sksYiYiIiATIJXS8ZDDokqMiIiIibXTij09eXt4FPXcuGskUEREREZ/jx49z9OhRGhoaOHToEG2n73z11VfU1NRc8HxUZIqIiIi00T5e/vf//t/8+te/pra2lszMTN/zPXv25IEHHrjg+ajIFBEREWnTSXZlB9KDDz7Igw8+yHPPPce//du/XfR8VGSKiIiIyBnuvfdeli9fznvvvYfD4eC6667j/vvvp2vXrhf0fhWZIiIiIgAOMLS73GfGjBlcdtllvtHMl19+mf/xP/4Hf/zjHy/o/ectMr1eL88//zzV1dVMmDCB0aNH+177xS9+wU9/+tOLjC4iIiJiM9pd7vPJJ59QVlbmezx27FjS09Mv+P3nrdfvu+8+3n33XeLj4/nRj37E/Pnzfa+tW7fuG8YVERERkc4gMzOT7du3+x5/+OGHZGdnX/D7zzuSWVJSwscffwzAAw88wNy5c5kyZQpr1qwhgHekFBEREQk+7S732bFjB9/5zndISkoCYN++fQwZMoShQ4ficDh89eG5nLfIbG5uPtk4KoqVK1fy85//nO9+97s0NTX5GV9ERERE7KioqMiv95+3Xs/Ozj7jQxYtWsTMmTOpqqry68NFREREbCNYd/vpJMd9DhgwgMbGRjZs2MCGDRtobGxkwIABvul8zltkvvTSS0yYMOGM5++9915OnDjhe/z2229/w+giIiIi9mJEBGfqDJ599lnuuece6urqqKur4/vf/z7PPffcBb/fsksY/fjHPyY/P9+q2YmIiIhICP3nf/4nH374IT169ADMWm/UqFEXfIF2y4pMnQQkoXZzxLRQRxCRS9CGljWhjuBjt7+Dduob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' style='max-width:100%; margin: auto; display: block; '/>

Feel free to experiment with that code or to build a benchmark using different
techniques and tools.
