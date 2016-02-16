/*
 * Check to see if the user has alerts, if so change the menu icon.
 * This will check every 60 seconds by default.
 */

$(document).ready(function() {
    // This uses a timeout so that if it fails (auth pages) it won't bother
    // trying agin until the page is refreshed.
    function has_alerts() {
        $.get("/alerts/new", function(data) {
            if (data.new_alerts > 0) {
                // Yey we have some alerts :-)
                $("#alert").addClass('alert');
            } else {
                // Oh no. We have no new alerts lets check again in a minute.
                setTimeout(function() {
                    has_alerts();
                }, 60000);
            }
        });
    }

    // Set an inital timeout.
    // This does not need to check straight away as the template render will
    // do that
    setTimeout(function() {
        has_alerts();
    }, 60000);
});
