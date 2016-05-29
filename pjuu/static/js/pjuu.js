$(document).ready(function() {

    /*
     * Flash messages from Javascript
     */
    function bind_message_removal() {
        $(".js-messages .message").click(function(event) {
            $(this).remove();
        });
    }

    function flash(message, category) {
        $(".js-messages .container").append("<div class=\"message " + category + "\">" + message + "</div>");
        bind_message_removal();
    }

    function clear_flashed_messages() {
        $(".js-messages .container").empty();
    }

    /*
     * Get the CSRF token for the user.
     */
    var csrftoken = $('meta[name=csrf-token]').attr('content')

    // Inject the post in to ALL POST ajax requests
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

    function ajaxAction(object, event, success) {
        event.preventDefault();
        form = object.parent("form");
        action = form.attr("action");
        method = form.attr("method");
        $.ajax(action, {
            method: method,
        }).success(function(data, textStatus, jqXHR) {
            clear_flashed_messages();
            flash(data.message, "success");
            success();
        }).error(function(jqXHR, textStatus, errorThrown) {
            data = jqXHR.responseJSON;
            flash(data.message, "error");
        });
    }

    // Voting
    $("body").on("click", "li.item.post form .upvote, #post li form .upvote", function(event) {
        upvote_button = $(this);
        downvote_button = $(this).closest("ul").find("form .downvoted");
        score = $(this).closest("ul").find(".score");
        ajaxAction(upvote_button, event, function() {
            upvote_button.removeClass("upvote");
            upvote_button.addClass("upvoted");

            if (!isNaN(Number(score.text()))) {
                amount = downvote_button.length ? 2 : 1;
                score.text(Number(score.text()) + amount);
            }

            downvote_button.removeClass("downvoted");
            downvote_button.addClass("downvote");
        });
    });

    $("body").on("click", "li.item.post form .upvoted, #post li form .upvoted", function(event) {
        upvote_button = $(this);
        score = $(this).closest("ul").find(".score");
        ajaxAction(upvote_button, event, function() {
            upvote_button.removeClass("upvoted");
            upvote_button.addClass("upvote");

            if (!isNaN(Number(score.text()))) {
                score.text(Number(score.text()) - 1)
            }
        });
    });

    $("body").on("click", "li.item.post form .downvote, #post li form .downvote", function(event) {
        downvote_button = $(this);
        upvote_button = $(this).closest("ul").find("form .upvoted");
        score = $(this).closest("ul").find(".score");
        ajaxAction(downvote_button, event, function() {
            downvote_button.removeClass("downvote");
            downvote_button.addClass("downvoted");

            if (!isNaN(Number(score.text()))) {
                amount = upvote_button.length ? 2 : 1;
                score.text(Number(score.text()) - amount);
            }

            upvote_button.removeClass("upvoted");
            upvote_button.addClass("upvote");
        });
    });

    $("body").on("click", "li.item.post form .downvoted, #post li form .downvoted", function(event) {
        downvote_button = $(this);
        score = $(this).closest("ul").find(".score");
        ajaxAction(downvote_button, event, function() {
            downvote_button.removeClass("downvoted");
            downvote_button.addClass("downvote");

            if (!isNaN(Number(score.text()))) {
                score.text(Number(score.text()) + 1)
            }
        });
    });
});
