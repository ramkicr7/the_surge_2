// ---------------- SEARCH FILTER ----------------

document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("searchInput");

    if (searchInput) {
        searchInput.addEventListener("keyup", function () {
            const value = this.value.toLowerCase();
            const items = document.querySelectorAll(".stock-item");

            items.forEach(item => {
                const text = item.innerText.toLowerCase();
                item.style.display = text.includes(value) ? "" : "none";
            });
        });
    }

});


// ---------------- AUTO REFRESH DASHBOARD ----------------

// Refresh page every 30 seconds (only on dashboard)
if (window.location.pathname === "/dashboard") {
    setTimeout(function () {
        location.reload();
    }, 30000); // 30 seconds
}


// ---------------- PRICE ANIMATION ----------------

document.addEventListener("DOMContentLoaded", function () {

    const prices = document.querySelectorAll(".stock-card h5");

    prices.forEach(price => {
        price.style.transition = "0.3s ease";
        price.style.transform = "scale(1.05)";
        setTimeout(() => {
            price.style.transform = "scale(1)";
        }, 300);
    });

});


// ---------------- FLASH MESSAGE AUTO HIDE ----------------

setTimeout(function () {
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        alert.style.transition = "opacity 0.5s";
        alert.style.opacity = "0";
        setTimeout(() => alert.remove(), 500);
    });
}, 3000);