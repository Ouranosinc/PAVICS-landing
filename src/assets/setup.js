/* Set up the template including the navbar */


/* Autosizes an iframe */
function autosizeIframes() {
  // Delay to ensure fully loaded
  setTimeout(function() {
    $("iframe").each(function() {
      // Can't resize if invisible
      if (!$(this).is(":visible")) {
        return
      }
      if (this.contentWindow.document.body) {
        this.style.height = (this.contentWindow.document.body.scrollHeight + 20) + 'px';
      }
      else {
        this.onload = () => {
          this.style.height = (this.contentWindow.document.body.scrollHeight + 20) + 'px';
        } 
      }
    })
  }, 100)
}

$(function() {
  // Load template
  $("body").load("assets/template.html", function() {
    // Get current page url
    const page = window.location.pathname.split("/")[window.location.pathname.split("/").length - 1]

    // Highlight nav-link
    $("li.nav-item").each(function() {
      // If current page, add active
      if ($(this).find("a").attr("href") == page) {
        $(this).addClass("active")
      }
    })

    // Add content
    $("#main").load("pages/" + page, function() {
      // Autosize iframes and redo whenever tab is clicked (as invisible ones can't be sized)
      autosizeIframes()
      $("a.nav-link").on("click", function() {
        autosizeIframes()
      })
    })
  })
})

