document.addEventListener("DOMContentLoaded", () => {
    console.log("✅ JS cargado OK");

    const form = document.getElementById("machineForm");
    const openBtn = document.getElementById("openSubmitMachine");
    const modal = document.getElementById("machineModal");
    const closeBtn = document.getElementById("closeModal");

    if (!form || !openBtn || !modal) {
        console.error("❌ Elementos del DOM no encontrados");
        return;
    }

    // =========================
    // MODAL CONTROL
    // =========================

    openBtn.addEventListener("click", () => {
        modal.style.display = "flex";
        console.log("🟢 modal abierto");
    });

    closeBtn?.addEventListener("click", () => {
        modal.style.display = "none";
    });

    window.addEventListener("click", (e) => {
        if (e.target === modal) {
            modal.style.display = "none";
        }
    });

    // =========================
    // SUBMIT FORM
    // =========================

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        console.log("🟡 submit interceptado");

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // ✅ CSRF CORRECTO (desde hidden input)
        const csrfToken = form.querySelector('input[name="csrf_token"]')?.value;

        console.log("🔐 CSRF TOKEN:", csrfToken);

        try {
            const res = await fetch("/api/submit-machine", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                body: JSON.stringify(data),
                credentials: "include"
            });

            console.log("🟢 petición enviada");

            const text = await res.text();

            let result;
            try {
                result = JSON.parse(text);
            } catch (err) {
                console.error("❌ Respuesta no es JSON:", text);
                return;
            }

            console.log("respuesta backend:", result);

            if (!res.ok) {
                console.error("❌ error backend:", result);
                return;
            }

            alert("✔ Máquina enviada correctamente");

            modal.style.display = "none";
            form.reset();

        } catch (error) {
            console.error("❌ error fetch:", error);
        }
    });
});
