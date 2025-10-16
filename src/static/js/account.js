function login(username, password) {
  return $.ajax({
    url: "/login",
    method: "POST",
    contentType: "application/json",
    xhrFields: { withCredentials: true },
    data: JSON.stringify({ username, password }),
  });
}

function checkAuth() {
  return $.ajax({
    url: "/api/music",
    method: "GET",
    xhrFields: { withCredentials: true },
  });
}

$(function () {
  checkAuth()
    .done(() => {
      $("#loginForm").removeClass("active");
    })
    .fail(() => {
      $("#loginForm").addClass("active");
    });
});

$(function () {
  $("#loginForm").on("submit", function (e) {
    e.preventDefault();
    const username = $("#username").val();
    const password = $("#password").val();
    login(username, password)
      .done(() => {
        notification("Logged in successfully");
        $("#loginForm").removeClass("active");
        offset = 0;
        noMore = false;
        const currentQuery = $("#searchbar").val().trim();
        if (currentQuery !== "") {
          performSearch(currentQuery);
        } else {
          loadBatch();
        }
      })
      .fail(() => notification("Login failed"));
  });
});
