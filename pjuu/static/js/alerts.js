/*
 * Check to see if the user has alerts, if so change the menu icon.
 * This will check every 20 seconds by default.
 */

// This uses a timeout so that if it fails (auth pages) it won't bother
// trying agin until the page is refreshed.
function has_alerts() {
    $.get("/i-has-alerts", function(data) {
        // Do we have alerts?
        if (data.result == true) {
            // We have alerts so change the image in the menu
            $("#alert-button").attr("src", "/static/img/glyphicons/new_alerts.png")
            // Don't bother looking for alerts again. It can only go red once
        } else {
            // We will not check that we don't have alerts and try and reset
            // the image. This will reduce overhead.
            // We will simply set a timeout to look again in 20 seconds
            setTimeout(function() {
                has_alerts();
            }, 20000);
        }
    })
}

// Set an inital timeout.
// This does not need to check straight away as the template render will
// do that
setTimeout(function() {
    has_alerts();
}, 20000);