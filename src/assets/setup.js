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
          let h = "#" + item.id;
          if (history.pushState) {
            history.pushState(null, null, h);
          }
          else {
            location.hash = h;
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

    // Called after loading of page is complete
    function afterLoad() {

      // Get the anchor at the end of the url, e.g. "src/hydrology.html#c" --> "#c"
      let anchor = window.location.hash;
      if (anchor) {
        // If the anchor is set, set the corresponding tab/item to active
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

      // Listen for tab changes
      $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        activateIframe()
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
