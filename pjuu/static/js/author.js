/*
 * Makes the authoring of posts more pleasant on various devices
 */

$(document).ready(function() {
    /* Simply displays the number of characters in a textarea */
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
});
