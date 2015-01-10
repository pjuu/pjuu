/*
 * Will ask a user to confirm via jQuery modal a deletion.
 */
$(".delete").click(function(event) {
    event.stopPropagation();
    var url = $(this).attr('href');
    if(confirm("Do you want to delete this post?")) {
        window.location = url;
    }
    event.preventDefault();
});