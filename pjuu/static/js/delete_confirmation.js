/* Will ask a user to confirm via jQuery modal a deletion. */
$(".delete").click(function(event) {
    event.stopPropagation();
    var url = $(this).closest("form").attr("action");
    if(!confirm("Do you want to delete this post?")) {
        event.preventDefault();
    }
});