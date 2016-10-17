$(document).ready(function() {

    /*
     * Flash messages from Javascript
     */

    // Clicking a JS flash message removes it
    $("body").on("click", ".js-messages .message", function(event) {
        $(this).remove();
    });

    // Make the messages also fade away after 10 seconds
    $('body').on('DOMNodeInserted', '.js-messages .message', function () {
          $(this).delay(10000).fadeTo("slow", 0);
    });

    function flash(message, category) {
        $(".js-messages .container").append("<div class=\"message " + category + "\">" + message + "</div>");
    }

    function clear_flashed_messages() {
        $(".js-messages .container").empty();
    }

    /*
     * Get the CSRF token for the user.
     */
    var csrftoken = $('meta[name=csrf-token]').attr('content')

    // Inject the token in to ALL POST ajax requests
    // http://flask-wtf.readthedocs.io/en/latest/csrf.html#ajax
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        }
    });

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
     * This feature does not work in Kitkat!
     */
    try {
        $('#upload-label').toggle(!Android.hideImageUpload());
    } catch (error) {
        $('#upload-label').toggle();
    }

    /*
     * Allow Ctrl+Enter to submit the post form
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
     * Un-follow/un-trust confirmation
     */
    $(".action.unfollow").click(function(event) {
        event.stopPropagation();
        if(!confirm("Are you sure you want to un-follow this user?")) {
            event.preventDefault();
        }
    });

    $(".action.unapprove").click(function(event) {
        event.stopPropagation();
        if(!confirm("Are you sure you no longer trust this user?")) {
            event.preventDefault();
        }
    });

    /*
     * Handle checking for new alerts
     */
    // The amount of time between checking for alerts
    var alert_timeout = 30000;

    // This uses a timeout so that if it fails (auth pages) it won't bother
    // trying again until the page is refreshed.
    function has_alerts() {
        $.get("/alerts/new", function(data) {
            if (data.new_alerts > 0) {
                // Yey we have some alerts :-)
                $("#alert").removeClass('fa-bell-o');
                $("#alert").addClass('fa-bell new-alert');
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

    /*
     * Change the trusted button on mouse actions.
     */
    $(".action.unapprove").hover (
        function() {
            $(this).html("Untrust")
        },
        function() {
            $(this).html("Trusted");
        }
    );

    /*
     * AJAX site actions
     */

    function voteAction(btn, event, vote) {
        // Stop the default action
        event.preventDefault();

        form = $(btn).parent("form");
        list = $(btn).closest("ul");

        // Get all the buttons and data we will for all vote actions
        var upvoteBtn = list.find("form .upvote, form .upvoted"),
            downvoteBtn = list.find("form .downvote, form .downvoted"),
            action = form.attr("action"),
            method = form.attr("method"),
            score = list.find(".score");

        // Disable all vote buttons on the post
        upvoteBtn.prop("disabled", true);
        downvoteBtn.prop("disabled", true);

        $.ajax(action, {
            method: method,
            timeout: 2000,
        }).success(function(data, textStatus, jqXHR) {
            clear_flashed_messages();
            flash(data.message, "success");

            console.log(vote);
            amount = 0;

            switch (vote) {
                case 'upvote':
                    amount = downvoteBtn.hasClass("downvoted") ? 2 : 1;
                    upvoteBtn.removeClass("upvote");
                    upvoteBtn.addClass("upvoted");
                    downvoteBtn.removeClass("downvoted");
                    downvoteBtn.addClass("downvote");
                    break;
                case 'upvoteReverse':
                    amount = -1;
                    upvoteBtn.removeClass("upvoted");
                    upvoteBtn.addClass("upvote");
                    downvoteBtn.removeClass("downvoted");
                    downvoteBtn.addClass("downvote");
                    break;
                case 'downvote':
                    amount = upvoteBtn.hasClass("upvoted") ? -2 : -1;
                    downvoteBtn.removeClass("downvote");
                    downvoteBtn.addClass("downvoted");
                    upvoteBtn.removeClass("upvoted");
                    upvoteBtn.addClass("upvote");
                    break;
                case 'downvoteReverse':
                    amount = 1;
                    downvoteBtn.removeClass("downvoted");
                    downvoteBtn.addClass("downvote");
                    upvoteBtn.removeClass("upvoted");
                    upvoteBtn.addClass("upvote");
                    break;
            }

            if (!isNaN(Number(score.text()))) {
                score.text(Number(score.text()) + amount);
            }
        }).error(function(jqXHR, textStatus, errorThrown) {
            clear_flashed_messages();
            if (jqXHR.status == 403) {
                flash("You need to be signed in to perform this action", "warning");
            } else {
                data = jqXHR.responseJSON;
                flash(data.message, "error");
            }
        }).always(function() {
            // Enable all votes buttons again and un-focus (blur) them
            upvoteBtn.blur();
            downvoteBtn.blur();
            upvoteBtn.prop("disabled", false);
            downvoteBtn.prop("disabled", false);
        });
    }

    // Upvote
    $("body").on("click", "li.item.post form .upvote, #post li form .upvote", function(event) {
        voteAction(this, event, 'upvote');
    });

    // Reverse upvote
    $("body").on("click", "li.item.post form .upvoted, #post li form .upvoted", function(event) {
        voteAction(this, event, 'upvoteReverse');
    });

    // Downvote
    $("body").on("click", "li.item.post form .downvote, #post li form .downvote", function(event) {
        voteAction(this, event, 'downvote');
    });

    // Reverse downvote
    $("body").on("click", "li.item.post form .downvoted, #post li form .downvoted", function(event) {
        voteAction(this, event, 'downvoteReverse');
    });

    /*
     * gifplayer
     */
    $('.gif').gifplayer();
});
