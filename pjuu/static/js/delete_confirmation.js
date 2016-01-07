/*
 * Allow confirmation of post deletion
 */

$(document).ready(function() {
    $(".delete").click(function(event) {
        event.stopPropagation();
        var url = $(this).closest("form").attr("action");
        if(!confirm("Do you want to delete this post?")) {
            event.preventDefault();
        }
    });
});
