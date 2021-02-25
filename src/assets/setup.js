/* Set up the template including the navbar */


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
    $("#main").load("pages/" + page)
  })
})

