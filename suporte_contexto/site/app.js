document.addEventListener("DOMContentLoaded", () => {
  const resultadoButtons = document.querySelectorAll(".btn-resultado");

  resultadoButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const newTab = window.open("resultado2.html", "_blank", "noopener,noreferrer");
      if (!newTab) {
        window.location.href = "resultado2.html";
      }
    });
  });
});
