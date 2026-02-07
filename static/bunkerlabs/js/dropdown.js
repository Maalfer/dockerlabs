// User dropdown toggle
document.addEventListener('DOMContentLoaded', function () {
    const dropdown = document.querySelector('.user-dropdown');

    if (dropdown) {
        const pill = dropdown.querySelector('.user-pill');
        const menu = dropdown.querySelector('.dropdown-menu');

        if (pill && menu) {
            pill.addEventListener('click', function (event) {
                event.preventDefault();
                event.stopPropagation();
                dropdown.classList.toggle('active');
                console.log('Dropdown toggled, active:', dropdown.classList.contains('active'));
            });

            // Prevent clicks inside the menu from closing it
            menu.addEventListener('click', function (event) {
                event.stopPropagation();
            });

            // Close when clicking outside
            document.addEventListener('click', function (event) {
                if (!dropdown.contains(event.target)) {
                    dropdown.classList.remove('active');
                }
            });
        } else {
            console.log('User pill or menu not found');
        }
    } else {
        console.log('User dropdown not found');
    }
});
