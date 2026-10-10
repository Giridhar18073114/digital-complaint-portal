const loginForm = document.getElementById("admin-login-form");

loginForm.addEventListener("submit", async function(event) {
    event.preventDefault();

    const password = document.getElementById("password").value;
    const message = document.getElementById("login-message");

    try {
        const response = await fetch("/admin-login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ password: password })
        });

        const result = await response.json();

        if (response.ok) {
            message.textContent = "Login successful!";
            window.location.href = "/admin-dashboard";
        } else {
            message.textContent = result.error || "Login failed.";
        }
    } catch (error) {
        message.textContent = "Cannot connect to the server.";
        console.error(error);
    }
});