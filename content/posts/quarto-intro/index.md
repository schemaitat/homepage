---
title: 'Hello, quarto.'
date: '2024-05-30'
categories:
  - tutorial
  - authoring
tags:
  - tutorial
  - quarto
  - markdown
  - jupyter
  - python
draft: true
---


<meta name="mermaid-theme" content="forest"/>
<script  src="index_files/libs/quarto-diagram/mermaid.min.js"></script>
<script  src="index_files/libs/quarto-diagram/mermaid-init.js"></script>
<link  href="index_files/libs/quarto-diagram/mermaid.css" rel="stylesheet" />

<script src="https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js" integrity="sha512-c3Nl8+7g4LMSTdrm621y7kf9v3SDPnhxLNhcjFJbKECVnmZHTdo+IRO05sNLTH/D3vA6u1X32ehoLC7WFVdheg==" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.5.1/jquery.min.js" integrity="sha512-bLT0Qm9VnAYZDflyKcBaQ2gg0hSYNQrJ8RilYldYQ1FxQYoCLtUjuuRuZo+fjqhx/qtq/1itJ0C2ejDxltZVFg==" crossorigin="anonymous" data-relocate-top="true"></script>
<script type="application/javascript">define('jquery', [],function() {return window.jQuery;})</script>


{{< admonition abstract >}}

**Things you get**
- A quick overview of how to integrate quarto with hugo.

**Prerequisites**
- Basic Linux and bash knowledge.

{{< /admonition  >}}

## Introduction

Looking into [quarto](https://quarto.org/) to write scientific articles with reproducible code execution has been on my to-do list for quite some time already. Quarto executes python cells and saves the output to markdown, called rendering. This markdown is then served by the static content generator hugo.

## Setup

Before we can start we need to install quarto. This can be done via an official installer or by installing a specific release. For the latter the following script can be used.

``` bash
# install quarto to ${HOME}/bin
QUARTO_VERSION=1.4.554

URL="https://github.com/quarto-dev/quarto-cli/releases/download/"\
"v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.tar.gz"

curl -o quarto.tar.gz -L $URL
tar -zxvf quarto.tar.gz
    --strip-components=1 \
    -C ${HOME}
rm quarto.tar.gz
```

{{< admonition info >}}

Make sure to use the right release specific to your operating system. I use the linux-amd64 release.

{{< /admonition  >}}

Next, I needed to add a `index.qmd` file to the root path to be able to call `quarto render` from the root path. This will render all `*.qmd` files in the project.

For the python runtime it is best practice to set up a virtual environment and install the basic jupyter requirement. I prefer `poetry` for dependency management and `uv` for creating virtual environments.
So, for me that basic step is

``` bash
uv venv --python 3.9 && source .venv/bin/activate && poetry install
```

where my `pyproject.toml` looks like this:

``` toml
[tool.poetry]
name = "homepage"
version = "0.1.0"
description = ""
authors = ["André Schemaitat <a.schemaitat@gmail.com>"]
readme = "README.md"
package-mode = false

[tool.poetry.dependencies]
python = "^3.9"
notebook = "^7.2.0"


[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

I added the `package-mode = false` setting, since I use poetry for dependency management only, i.e. housekeeping my venv.

{{< admonition info >}}

Don't forget to activate your venv when calling `quarto render`.

{{< /admonition  >}}

Finally, you can (and it makes sense) add a configuration file `_quarto.yml` to the root path, which contains the global quarto configuration. Right now, I use the following setup:

``` yaml
project:
  type: hugo
      
format:
  hugo-md: 
    mermaid: 
      theme: forest

jupyter: python3

editor: 
  render-on-save: true
```

However, you can also add quarto settings per document. These will then be merged with the global settings.

## Workflow

The main steps of creating content with quarto and hugo are depicted in <a href="#fig-workflow" class="quarto-xref">Figure 1</a>.

<div id="fig-workflow">

<pre class="mermaid mermaid-js" data-label="fig-workflow">
graph LR;
    A(qmd) --&gt; 
    B(jupyter)
    --&gt; C(md)
    --&gt; D(Pandoc)
    --&gt; E(hugo md)
    A --&gt;|quarto render| E
    E --&gt;|hugo serve| F(html)
</pre>

Figure 1: Quarto & hugo workflow.
</div>

We first write some content, a quarto markdown file (\*.qmd), that might contain [diagrams](https://quarto.org/docs/authoring/diagrams.html) (mermaid, graphviz, ...) or python code and then render the file with quarto. You can choose from many different output formats; we will need `hugo-md`, which is a hugo compatible markdown file.

You can then run `quarto preview` from the root path, which will run a `hugo serve` command for you and call `quarto render` on changes.

## IDE

For VS Code you can install the quarto extension. This gets you some basic shortcuts for running quarto commands (e.g. quarto preview).
But something for me really useful is the preview functionality for diagrams. It lets you create mermaid diagrams or graphviz graphs on the fly and see the changes in a split screen live view !

<figure>
<img src="images/quarto-preview.png" alt="Diagram preview" />
<figcaption aria-hidden="true">Diagram preview</figcaption>
</figure>

## Deployment

For the deployment of this homepage, I use a simple Jenkins CI/CD Pipeline. Here CI means building the website html and CD means simply copying the html to a folder on the same machine that is served by nginx.
When using quarto we have the additional `quarto render` step, that has to be executed before running `hugo`, which builds the html content. As described earlier we also need to install some binaries and a python environment to be able to run `quarto render`.
Installing the required binaries into `${HOME}/bin` on a CentOS machine could look like this:

``` bash
#!/bin/bash
# filename: install.sh

rm -rf ${HOME}/bin
mkdir -p ${HOME}/bin
mkdir -p ${HOME}/poetry

# install quarto
export QUARTO_VERSION=1.4.554

curl -o quarto.tar.gz -L \
    "https://github.com/quarto-dev/quarto-cli/releases/download/"\
"v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.tar.gz"

tar -zxvf quarto.tar.gz \
    --strip-components=1 \
    -C ${HOME}
rm quarto.tar.gz

# install uv
export UV_RELEASE=0.1.44

curl -o uv.tar.gz -L \
    "https://github.com/astral-sh/uv/releases/download/"\
"${UV_RELEASE}/uv-x86_64-unknown-linux-gnu.tar.gz"

tar -zxvf uv.tar.gz \
    --strip-components=1 \
    -C ${HOME}/bin

rm uv.tar.gz

# install hugo
export HUGO_RELEASE=0.108.0

curl -o hugo.tar.gz -L \
    "https://github.com/gohugoio/hugo/releases/download/"\
"v${HUGO_RELEASE}/hugo_extended_${HUGO_RELEASE}_Linux-64bit.tar.gz"

tar -zxvf hugo.tar.gz -C ${HOME}/bin
rm hugo.tar.gz

# install poetry
curl -sSL https://install.python-poetry.org | POETRY_HOME=${HOME}/bin/poetry python3 -

# make all binaries executable
chmod -R +x ${HOME}/bin
```

My current `Jenkinsfile` looks like this:

``` jenkins
pipeline{
    agent any

    environment{
        // look at local installation of hugo first if a 
        // installation with the wrong version exists
        PATH="${HOME}/bin:${HOME}/bin/poetry/bin:${WORKSPACE}:${PATH}"
    }

    stages {
        stage('Update submodules') {
            steps{
                sh "git submodule update --init --recursive"
            }
        }   

        stage('Install binaries'){
            steps{
                sh'''#!/bin/bash
                chmod +x ./scripts/install.sh
                ./scripts/install.sh
                '''
            }
        }

        stage('Create python venv and install packages'){
            steps{
                sh'''#!/bin/bash
                # as required by pyproject
                uv venv --python 3.9
                source .venv/bin/activate
                poetry install
                '''
            }
        }

        stage('Build static HTML') {
            steps{
                sh'''#!/bin/bash
                set -x
                sed -i "s/{{COMMIT}}/${GIT_COMMIT:0:6}/g" config.toml
                sed -i "s/{{DATE}}/$(date '+%A %e %B %Y')/g" config.toml
                '''
                sh "rm -rf public"
                sh "poetry run quarto render && hugo --cacheDir $HOME/hugo_cache"
            }
        }   

        stage("Update HTML"){
            steps{
                sh'''#!/bin/bash
                set -x
                rm -rf /usr/share/nginx/html/*
                cp -r public/* /usr/share/nginx/html
                '''
            }
        }
    }        
}
```

The relevant parts are adding `${HOME}/bin` to the `$PATH`, installing the binaries with our magic script, creating the venv with the correct python version, installing the python project and running the quarto render hugo workflow.

## Python Example

Finally, because it is so much fun, I want to showcase a simple python example. It uses the fantastic tool [polars](https://pola.rs/). The data file lives in the root path of this post and is called `clean_data.csv`.

{{< admonition note >}}

Since polars is my newly loved and absolute favorite data processing library (thanks to Ritchie Vink), I will hopefully find some time to write a few posts about this tool and how a data scientist can benefit from it.

{{< /admonition  >}}

``` python
import polars as pl
import hvplot

hvplot.extension("matplotlib")

df = (
  pl.scan_csv("clean_data.csv")
  .select(["year", "month", "stateDescription", "price", "sales"])
  .rename({
    "stateDescription" : "state"
  })
  .filter(pl.col("state").str.contains("^(A|B|C)"))
  .with_columns(
    date=pl.date(pl.col("year"), pl.col("month"), 1),
  )
  .group_by_dynamic(
    "date",
    every="60d",
    group_by="state",
  )
  .agg(
    total_sales = pl.col("sales").sum(),
  )
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
<div id='p1030'>
  <div id="b437924f-f8e5-4cde-9604-6f5e187570ae" data-root-id="p1030" style="display: contents;"></div>
</div>
<script type="application/javascript">(function(root) {
  var docs_json = {"3ca0454f-71b7-4f96-b6d0-adc0a59d151f":{"version":"3.4.1","title":"Bokeh Application","roots":[{"type":"object","name":"panel.models.browser.BrowserInfo","id":"p1030"},{"type":"object","name":"panel.models.comm_manager.CommManager","id":"p1031","attributes":{"plot_id":"p1030","comm_id":"5ac79e7478a0459f9fdce5c761e94f0e","client_comm_id":"67cac7812fff49e1b5a101c92edc4004"}}],"defs":[{"type":"model","name":"ReactiveHTML1"},{"type":"model","name":"FlexBox1","properties":[{"name":"align_content","kind":"Any","default":"flex-start"},{"name":"align_items","kind":"Any","default":"flex-start"},{"name":"flex_direction","kind":"Any","default":"row"},{"name":"flex_wrap","kind":"Any","default":"wrap"},{"name":"gap","kind":"Any","default":""},{"name":"justify_content","kind":"Any","default":"flex-start"}]},{"type":"model","name":"FloatPanel1","properties":[{"name":"config","kind":"Any","default":{"type":"map"}},{"name":"contained","kind":"Any","default":true},{"name":"position","kind":"Any","default":"right-top"},{"name":"offsetx","kind":"Any","default":null},{"name":"offsety","kind":"Any","default":null},{"name":"theme","kind":"Any","default":"primary"},{"name":"status","kind":"Any","default":"normalized"}]},{"type":"model","name":"GridStack1","properties":[{"name":"mode","kind":"Any","default":"warn"},{"name":"ncols","kind":"Any","default":null},{"name":"nrows","kind":"Any","default":null},{"name":"allow_resize","kind":"Any","default":true},{"name":"allow_drag","kind":"Any","default":true},{"name":"state","kind":"Any","default":[]}]},{"type":"model","name":"drag1","properties":[{"name":"slider_width","kind":"Any","default":5},{"name":"slider_color","kind":"Any","default":"black"},{"name":"value","kind":"Any","default":50}]},{"type":"model","name":"click1","properties":[{"name":"terminal_output","kind":"Any","default":""},{"name":"debug_name","kind":"Any","default":""},{"name":"clears","kind":"Any","default":0}]},{"type":"model","name":"FastWrapper1","properties":[{"name":"object","kind":"Any","default":null},{"name":"style","kind":"Any","default":null}]},{"type":"model","name":"NotificationAreaBase1","properties":[{"name":"js_events","kind":"Any","default":{"type":"map"}},{"name":"position","kind":"Any","default":"bottom-right"},{"name":"_clear","kind":"Any","default":0}]},{"type":"model","name":"NotificationArea1","properties":[{"name":"js_events","kind":"Any","default":{"type":"map"}},{"name":"notifications","kind":"Any","default":[]},{"name":"position","kind":"Any","default":"bottom-right"},{"name":"_clear","kind":"Any","default":0},{"name":"types","kind":"Any","default":[{"type":"map","entries":[["type","warning"],["background","#ffc107"],["icon",{"type":"map","entries":[["className","fas fa-exclamation-triangle"],["tagName","i"],["color","white"]]}]]},{"type":"map","entries":[["type","info"],["background","#007bff"],["icon",{"type":"map","entries":[["className","fas fa-info-circle"],["tagName","i"],["color","white"]]}]]}]}]},{"type":"model","name":"Notification","properties":[{"name":"background","kind":"Any","default":null},{"name":"duration","kind":"Any","default":3000},{"name":"icon","kind":"Any","default":null},{"name":"message","kind":"Any","default":""},{"name":"notification_type","kind":"Any","default":null},{"name":"_destroyed","kind":"Any","default":false}]},{"type":"model","name":"TemplateActions1","properties":[{"name":"open_modal","kind":"Any","default":0},{"name":"close_modal","kind":"Any","default":0}]},{"type":"model","name":"BootstrapTemplateActions1","properties":[{"name":"open_modal","kind":"Any","default":0},{"name":"close_modal","kind":"Any","default":0}]},{"type":"model","name":"TemplateEditor1","properties":[{"name":"layout","kind":"Any","default":[]}]},{"type":"model","name":"MaterialTemplateActions1","properties":[{"name":"open_modal","kind":"Any","default":0},{"name":"close_modal","kind":"Any","default":0}]},{"type":"model","name":"copy_to_clipboard1","properties":[{"name":"fill","kind":"Any","default":"none"},{"name":"value","kind":"Any","default":null}]}]}};
  var render_items = [{"docid":"3ca0454f-71b7-4f96-b6d0-adc0a59d151f","roots":{"p1030":"b437924f-f8e5-4cde-9604-6f5e187570ae"},"root_ids":["p1030"]}];
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

``` python
df.collect().plot.line(x="date", y="total_sales", by="state")
```

<img src='data:image/png;base64,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' style='max-width:100%; margin: auto; display: block; '/>
{{< admonition tip >}}

Since we are running a jupyter python kernel we are also allowed to run inline shell scripts with the `%%sh` cell magic !

``` python
%%sh
set -x
echo "Hello world from $(hostname) !"
pwd
ls -alh . | grep -i csv
curl wttr.in/Münster
set +x
```

    ++ hostname
    + echo 'Hello world from MacBook-Pro.local !'
    + pwd
    + ls -alh .
    + grep -i csv
    + curl wttr.in/Münster
      % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                     Dload  Upload   Total   Spent    Left  Speed
      0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0100  9080  100  9080    0     0   211k      0 --:--:-- --:--:-- --:--:--  216k
    + set +x

    Hello world from MacBook-Pro.local !
    /Users/andre/projects/homepage/content/posts/quarto-intro
    -rw-rw-r--@  1 andre  staff   4,9M  7 Apr 19:18 clean_data.csv
    Weather report: Münster

          \   /     Clear
           .-.      16 °C          
        ― (   ) ―   ↘ 4 km/h       
           `-’      10 km          
          /   \     0.0 mm         
                                                           ┌─────────────┐                                                       
    ┌──────────────────────────────┬───────────────────────┤  Thu 30 May ├───────────────────────┬──────────────────────────────┐
    │            Morning           │             Noon      └──────┬──────┘     Evening           │             Night            │
    ├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
    │  _`/"".-.     Patchy rain ne…│  _`/"".-.     Patchy rain ne…│  _`/"".-.     Patchy rain ne…│     \   /     Clear          │
    │   ,\_(   ).   16 °C          │   ,\_(   ).   19 °C          │   ,\_(   ).   18 °C          │      .-.      +16(12) °C     │
    │    /(___(__)  → 7-8 km/h     │    /(___(__)  → 8-10 km/h    │    /(___(__)  ↘ 13-18 km/h   │   ― (   ) ―   ↘ 4-23 km/h    │
    │      ‘ ‘ ‘ ‘  10 km          │      ‘ ‘ ‘ ‘  9 km           │      ‘ ‘ ‘ ‘  9 km           │      `-’      10 km          │
    │     ‘ ‘ ‘ ‘   0.0 mm | 60%   │     ‘ ‘ ‘ ‘   0.4 mm | 100%  │     ‘ ‘ ‘ ‘   0.4 mm | 100%  │     /   \     0.0 mm | 73%   │
    └──────────────────────────────┴──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
                                                           ┌─────────────┐                                                       
    ┌──────────────────────────────┬───────────────────────┤  Fri 31 May ├───────────────────────┬──────────────────────────────┐
    │            Morning           │             Noon      └──────┬──────┘     Evening           │             Night            │
    ├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
    │  _`/"".-.     Patchy rain ne…│  _`/"".-.     Patchy rain ne…│  _`/"".-.     Patchy rain ne…│    \  /       Partly Cloudy  │
    │   ,\_(   ).   13 °C          │   ,\_(   ).   17 °C          │   ,\_(   ).   18 °C          │  _ /"".-.     +14(13) °C     │
    │    /(___(__)  → 10-14 km/h   │    /(___(__)  → 11-13 km/h   │    /(___(__)  → 15-21 km/h   │    \_(   ).   ↘ 10-20 km/h   │
    │      ‘ ‘ ‘ ‘  10 km          │      ‘ ‘ ‘ ‘  10 km          │      ‘ ‘ ‘ ‘  10 km          │    /(___(__)  10 km          │
    │     ‘ ‘ ‘ ‘   0.0 mm | 61%   │     ‘ ‘ ‘ ‘   0.1 mm | 100%  │     ‘ ‘ ‘ ‘   0.0 mm | 70%   │               0.0 mm | 0%    │
    └──────────────────────────────┴──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
                                                           ┌─────────────┐                                                       
    ┌──────────────────────────────┬───────────────────────┤  Sat 01 Jun ├───────────────────────┬──────────────────────────────┐
    │            Morning           │             Noon      └──────┬──────┘     Evening           │             Night            │
    ├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
    │  _`/"".-.     Patchy rain ne…│  _`/"".-.     Light rain sho…│  _`/"".-.     Patchy rain ne…│    \  /       Partly Cloudy  │
    │   ,\_(   ).   17 °C          │   ,\_(   ).   20 °C          │   ,\_(   ).   20 °C          │  _ /"".-.     16 °C          │
    │    /(___(__)  ↓ 13-16 km/h   │    /(___(__)  ↓ 18-23 km/h   │    /(___(__)  ↘ 22-32 km/h   │    \_(   ).   ↘ 20-31 km/h   │
    │      ‘ ‘ ‘ ‘  10 km          │      ‘ ‘ ‘ ‘  10 km          │      ‘ ‘ ‘ ‘  10 km          │    /(___(__)  10 km          │
    │     ‘ ‘ ‘ ‘   0.0 mm | 67%   │     ‘ ‘ ‘ ‘   0.2 mm | 100%  │     ‘ ‘ ‘ ‘   0.1 mm | 100%  │               0.0 mm | 0%    │
    └──────────────────────────────┴──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
    Location: Münster, Regierungsbezirk Münster, Nordrhein-Westfalen, Deutschland [51.9501317,7.61330165026119]

    Follow @igor_chubin for wttr.in updates

{{< /admonition  >}}
