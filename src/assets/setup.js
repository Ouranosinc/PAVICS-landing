/* Set up the template including the navbar */


$(function() {
  // Determine template
  var template
  if (window.location.pathname.match(/_fr\.html/)) {
    template = "assets/template_fr.html"
  }
  else {
    template = "assets/template.html"
  }

  // Load template
  $("body").load(template, function() {
    // Get current page url
    const page = window.location.pathname.split("/")[window.location.pathname.split("/").length - 1]

    // Highlight nav-link
    $("li.nav-item").each(function() {
      // If current page, add active
      if ($(this).find("a").attr("href") == page) {
        $(this).addClass("active")
      }
    })

    // Creates and activates any iframes. Use data-iframe to load an iframe in tab.
    // Use data-pavics-link to open in PAVICS. Link text goes in data-pavics-link-text
    function activateIframe() {
      $(".tab-pane.active").each(function(index, item) {
        if ($(item).data("iframe")) {

          // Update the location bar url with the item hash
          let anchor = "#" + item.id;
          if (window.history.pushState) {
            window.history.pushState(null, null, anchor);
          }
          else {
            window.location.hash = anchor;
          }

          html = ''

          // Add pavics link
          if ($(item).data("pavics-link")) {
            html += '<div class="open-in-pavics">'
            html += '  <a target="_blank" href="' + $(item).data("pavics-link") + '">'
            html += $(item).data("pavics-link-text")
            html += '  </a>'
            html += '</div>'
          }

          // Add spinner and iframe
          html += '<img id="spinner" style="width: 100%" src="assets/images/loading-image.gif">'

          html += '<iframe src="' + $(item).data("iframe") + '" frameBorder="0" style="width: 100%; height: 120vh" onload="finishLoadingIframe()"></iframe>'
          $(item).html(html)

          // Prevent loading twice
          $(item).data("iframe", "")
        }
      })
    }

    // Dataset notebook browser support
    var datasetNotebookManifest = null

    function encodeHTML(value) {
      return $('<div/>').text(value).html()
    }

    function getDatasetManifest(callback) {
      if (datasetNotebookManifest) {
        callback(datasetNotebookManifest)
        return
      }
      $.getJSON("assets/datasets-notebooks.json").done(function(data) {
        datasetNotebookManifest = data
        callback(data)
      }).fail(function() {
        console.error("Unable to load dataset manifest from assets/datasets-notebooks.json")
      })
    }

    function setupDatasetBrowser(page) {
      if (page !== "datasets.html" && page !== "datasets_fr.html") {
        return
      }

      getDatasetManifest(function(manifest) {
        const isFrench = page === "datasets_fr.html"
        const activePane = $(".tab-pane.active")
        if (!activePane.length) {
          return
        }

        const category = activePane.data("category") || "Datasets_1-Climate_Simulations"
        const categoryData = manifest[category]
        if (!categoryData) {
          activePane.html('<div class="alert alert-warning">' + (isFrench ? 'La catégorie de jeux de données est introuvable.' : 'Dataset category not found.') + '</div>')
          return
        }

        let browser = activePane.find("#dataset-browser")
        if (!browser.length) {
          activePane.empty()
          browser = $(
            '<div id="dataset-browser" class="dataset-browser">' +
              '<div class="form-row">' +
                '<div class="form-group col-12">' +
                  '<label for="dataset-folder-select">' + (isFrench ? 'Institution' : 'Institution') + '</label>' +
                  '<select id="dataset-folder-select" class="form-control"></select>' +
                '</div>' +
                '<div class="form-group col-12">' +
                  '<select id="dataset-file-select" class="form-control"></select>' +
                '</div>' +
              '</div>' +
              '<div id="dataset-iframe-wrapper" class="dataset-iframe-wrapper">' +
                '<img id="dataset-spinner" style="width:100%;display:none;" src="assets/images/loading-image.gif" alt="Loading...">' +
                '<iframe id="dataset-viewer" src="" frameborder="0" style="display:none; width:100%; height:120vh;" onload="datasetIframeLoaded(this)"></iframe>' +
              '</div>' +
            '</div>'
          )
          activePane.append(browser)
        }

        const folderSelect = activePane.find("#dataset-folder-select")
        const fileSelect = activePane.find("#dataset-file-select")
        const spinner = activePane.find("#dataset-spinner")
        const viewer = activePane.find("#dataset-viewer")
        const subfolders = categoryData.subfolders || {}
        const folderNames = Object.keys(subfolders)

        function getFileCandidates(files) {
          const preferred = isFrench
            ? files.filter(function(file) { return file.endsWith("_fr.html") })
            : files.filter(function(file) { return !file.endsWith("_fr.html") })
          return preferred.length ? preferred : files.slice()
        }

        function setIframeSource(filePath) {
          if (!filePath) {
            viewer.hide()
            spinner.hide()
            return
          }
          const url = categoryData.path + "/" + filePath
          viewer.hide()
          spinner.show()
          viewer.attr("src", encodeURI(url))
        }

        function loadSelectedFile() {
          const selectedFile = fileSelect.val()
          setIframeSource(selectedFile)
        }

        function makeLabel(fileName) {
          return fileName.replace(/_fr\.html$/, "").replace(/\.html$/, "").trim()
        }

        function populateFileSelect(folderName) {
          const files = subfolders[folderName] || []
          const candidates = getFileCandidates(files)
          fileSelect.empty()

          if (!candidates.length) {
            fileSelect.append('<option value="">' + (isFrench ? 'Aucun fichier disponible' : 'No files available') + '</option>')
            setIframeSource("")
            return
          }

          candidates.forEach(function(file) {
            fileSelect.append('<option value="' + encodeHTML(folderName + "/" + file) + '">' + encodeHTML(makeLabel(file)) + '</option>')
          })
          fileSelect.val(folderName + "/" + candidates[0])
          loadSelectedFile()
        }

        folderSelect.empty()
        if (!folderNames.length) {
          folderSelect.append('<option value="">' + (isFrench ? 'Aucun groupe disponible' : 'No dataset groups available') + '</option>')
          fileSelect.empty()
          setIframeSource("")
          return
        }

        folderNames.forEach(function(name) {
          folderSelect.append('<option value="' + encodeHTML(name) + '">' + encodeHTML(name) + '</option>')
        })

        folderSelect.off("change").on("change", function() {
          populateFileSelect($(this).val())
        })

        fileSelect.off("change").on("change", loadSelectedFile)

        if (!folderSelect.val()) {
          folderSelect.val(folderNames[0])
        }
        populateFileSelect(folderSelect.val())
      })
    }

    window.datasetIframeLoaded = function(iframe) {
      $(iframe).show()
      $(iframe).siblings("#dataset-spinner").hide()
    }

    // Called after loading of page is complete
    function afterLoad() {

      // Get the anchor at the end of the url, e.g. "src/hydrology.html#c" --> "#c"
      let anchor = window.location.hash;
      if (anchor) {
        // If the anchor is set, first set the default (i.e. the first) tab and item to inactive, then
        // set the user selected tab and item to active
        $("#a.tab-pane").removeClass("show active");
        $(`${anchor}.tab-pane`).addClass("show active");
        $("a.nav-link").each(function() {
          if ($(this).attr("href") === "#a") {
            $(this).removeClass("active")
          }
        });
        $("a.nav-link").each(function() {
          if ($(this).attr("href") === anchor) {
            $(this).addClass("active")
          }
        });
      }

      // Activate initial iframe
      activateIframe()
      setupDatasetBrowser(page)

      // Listen for tab changes
      $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        activateIframe()
        setupDatasetBrowser(page)
      })
   }


    // Add content
    $("#main").load("pages/" + page, afterLoad)
  })
})

/* Called when iframe is finished loading */
function finishLoadingIframe() {
  // Hide spinner
  $("#spinner").remove()
}

/** Switch to the other language */
function switchLanguage() {
  const path = window.location.pathname
  if (path == "/") {
    window.location.href = "/index_fr.html"
    return
  }

  // English is just French without _fr
  if (path.match(/_fr\.html/)) {
    window.location.href = path.replace("_fr.html", ".html")
    return
  }

  window.location.href = path.replace(".html", "_fr.html")
}
