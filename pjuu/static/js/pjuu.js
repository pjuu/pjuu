$(document).ready(function() {

    /*
     * Author actions
     */
    $('textarea').bind('input propertychange', function() {
        var length = $(this).val().length;
        var max_length = $(this).attr("maxLength");
        $(this).siblings("#count").text(length + " / " + max_length);
        $(this).siblings("#count").css('color', 'rgb(' + (length / 2 + 5 ) +', 0, 0)');
    });

    /* Change the image icon when a file has been added to the input */
    $('#upload').bind('change', function() {
        var fileName = $("#upload").val();
        if (fileName) {
            $('#upload-label').addClass('has-file');
        } else {
            $('#upload-label').removeClass('has-file');
        }
    });

    /*
     * Remove image upload field if it is set in the JS. Mainly for Android.
     * If there is a function defined within the Android app this will not show.
     */
    try {
        $('#upload-label').toggle(!Android.hideImageUpload());
    } catch (error) {
        $('#upload-label').toggle();
    }

    /*
     * Allow Ctrl+Enter to submit the auth form
     */
    $('#author #body').keydown(function (event) {
        if (event.ctrlKey && (event.keyCode == 10 || event.keyCode == 13)) {
            $(this).closest('form').submit();
        }
    });

    /*
     * Delete/Hide confirmations
     */
    $(".delete").click(function(event) {
        event.stopPropagation();
        if(!confirm("Do you want to delete this post?")) {
            event.preventDefault();
        }
    });

    $(".post .hide").click(function(event) {
        event.stopPropagation();
        if(!confirm("Do you want to hide this post?")) {
            event.preventDefault();
        }
    });

    $(".alert .hide").click(function(event) {
        event.stopPropagation();
        if(!confirm("Do you want to hide this alert?")) {
            event.preventDefault();
        }
    });

    /*
     * Handle checking for new alerts
     */
    // The amount of time between checking for alerts
    var alert_timeout = 5000;

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
                }, alert_timeout);
            }
        });
    }

    // Set an inital timeout.
    // This does not need to check straight away as the template render will
    // do that
    setTimeout(function() {
        has_alerts();
    }, alert_timeout);

    /*
     * Change the follow buttons on mouse actions.
     */
    $(".action.unfollow").hover(
        function() {
            $(this).text("Unfollow")
        },
        function() {
            $(this).text("Following");
        }
    );

    $(".action.you").hover(
        function() {
            $(this).html("Edit")
        },
        function() {
            $(this).html("You");
        }
    );

});
