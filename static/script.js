function darkMode(){

    document.body.classList.toggle("dark");

}
document.querySelectorAll('.progress-fill').forEach(function(bar){

    let width = bar.getAttribute('data-width');

    bar.style.width = width + "%";

});