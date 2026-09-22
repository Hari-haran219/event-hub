// Client-side enhancements for Online Event Registration and Management System

document.addEventListener("DOMContentLoaded", function () {
    // Auto-dismiss flash messages after 5 seconds
    document.querySelectorAll(".flash").forEach(function (flash) {
        setTimeout(function () {
            flash.style.transition = "opacity 0.4s";
            flash.style.opacity = "0";
            setTimeout(function () { flash.remove(); }, 400);
        }, 5000);
    });

    // Client-side password confirmation check (registration form)
    const confirmField = document.getElementById("confirm_password");
    const passwordField = document.getElementById("password");
    const registerForm = confirmField ? confirmField.closest("form") : null;

    if (registerForm && passwordField) {
        registerForm.addEventListener("submit", function (e) {
            if (passwordField.value !== confirmField.value) {
                e.preventDefault();
                showInlineError(confirmField, "Passwords do not match.");
            }
        });
    }

    // Prevent past dates being picked for event_date (extra client-side guard)
    const eventDateInput = document.getElementById("event_date");
    if (eventDateInput && !eventDateInput.value) {
        const today = new Date().toISOString().split("T")[0];
        eventDateInput.setAttribute("min", today);
    }

    function showInlineError(field, message) {
        let err = field.parentElement.querySelector(".inline-error");
        if (!err) {
            err = document.createElement("small");
            err.className = "inline-error";
            err.style.color = "#dc2626";
            err.style.display = "block";
            err.style.marginTop = "4px";
            field.parentElement.appendChild(err);
        }
        err.textContent = message;
    }
});
