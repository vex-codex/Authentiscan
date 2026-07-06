const form = document.getElementById("loginForm");

form.addEventListener("submit", async (e) => {

    e.preventDefault();

    const username = document.getElementById("username").value;

    const password = document.getElementById("password").value;

    try {

        const response = await fetch("/login", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                username,
                password
            })

        });

        const data = await response.json();

        if (response.ok) {

            localStorage.setItem(
                "token",
                data.access_token
            );

           window.location = "/dashboard";

        } else {

            document.getElementById("message").innerText =
                data.detail;

        }

    } catch {

        document.getElementById("message").innerText =
            "Server not available.";

    }

});