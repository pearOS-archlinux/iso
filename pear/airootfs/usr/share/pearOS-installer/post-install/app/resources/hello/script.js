const hello = document.querySelector(".hello__div");
setInterval(hello__function, 20000);
function hello__function() {
  hello.style.display = "none";
  setTimeout(function () {
    hello.style.display = "flex";
  }, 10);
}