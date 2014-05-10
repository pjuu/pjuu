/* Simply displays the number of characters in a textarea */
$('textarea').bind('input propertychange', function() {
    var length = $(this).val().length;
    var max_length = $(this).attr("maxLength") || 255;
    $(this).siblings("#character-count").text(length + "/" + max_length);
    if (length > max_length) {
        $(this).closest('form').find(':submit').attr('disabled', 'disabled');
        $(this).siblings("#character-count").css('color', '#F00');
    } else {
        $(this).closest('form').find(':submit').removeAttr('disabled');
        $(this).siblings("#character-count").css('color', '#000');
    }
});