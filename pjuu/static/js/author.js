/* Simply displays the number of characters in a textarea */
$('textarea').bind('input propertychange', function() {
    var length = $(this).val().length;
    var max_length = $(this).attr("maxLength");
    $(this).siblings("#count").text(length + " / " + max_length);
    if (length > max_length) {
        $(this).closest('form').find(':submit').attr('disabled', 'disabled');
        $(this).siblings("#count").css('color', '#F00');
    } else {
        $(this).closest('form').find(':submit').removeAttr('disabled');
        $(this).siblings("#count").css('color', '#000');
    }
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