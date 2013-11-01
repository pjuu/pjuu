$("#author-hider").click(function() {
    $("#author").toggle();
    if ($("#author").is(":hidden")) {
        $("#author-hider").css("margin", "0.5em 0");
    } else {
        $("#author-hider").css("margin", "0.5em 0 0");
        $("#body").focus()
    }
});
