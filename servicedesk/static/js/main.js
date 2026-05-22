/**
 * Service Desk - Main JavaScript
 * Vanilla-first approach - no dependencies
 */

(function() {
    'use strict';

    /**
     * Initialize the application when DOM is ready.
     */
    function init() {
        initAlertDismiss();
        initFormValidation();
        initConfirmActions();
        initTableSort();
        initDropdownNavigation();
    }

    /**
     * Auto-dismiss flash messages after delay.
     */
    function initAlertDismiss() {
        var alerts = document.querySelectorAll('.alert');
        var DISMISS_DELAY_MS = 5000;

        alerts.forEach(function(alert) {
            setTimeout(function() {
                if (alert && alert.parentNode) {
                    alert.style.opacity = '0';
                    alert.style.transition = 'opacity 0.3s ease';
                    setTimeout(function() {
                        if (alert.parentNode) {
                            alert.parentNode.removeChild(alert);
                        }
                    }, 300);
                }
            }, DISMISS_DELAY_MS);
        });
    }

    /**
     * Enhanced form validation with accessibility support.
     */
    function initFormValidation() {
        var forms = document.querySelectorAll('form[data-validate]');

        forms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                var requiredFields = form.querySelectorAll('[required]');
                var isValid = true;
                var firstInvalid = null;

                requiredFields.forEach(function(field) {
                    // Clear previous validation state
                    field.classList.remove('form-control--error');
                    field.removeAttribute('aria-invalid');

                    if (!field.value.trim()) {
                        isValid = false;
                        field.classList.add('form-control--error');
                        field.setAttribute('aria-invalid', 'true');
                        if (!firstInvalid) {
                            firstInvalid = field;
                        }
                    }
                });

                if (!isValid) {
                    e.preventDefault();
                    announce('Please fill in all required fields.');
                    if (firstInvalid) {
                        firstInvalid.focus();
                    }
                }
            });

            // Real-time validation feedback
            var inputs = form.querySelectorAll('.form-control[required]');
            inputs.forEach(function(input) {
                input.addEventListener('blur', function() {
                    if (!input.value.trim()) {
                        input.classList.add('form-control--error');
                        input.setAttribute('aria-invalid', 'true');
                    } else {
                        input.classList.remove('form-control--error');
                        input.removeAttribute('aria-invalid');
                    }
                });
            });
        });
    }

    /**
     * Confirm dangerous actions with accessible dialog.
     */
    function initConfirmActions() {
        var confirmButtons = document.querySelectorAll('[data-confirm]');

        confirmButtons.forEach(function(button) {
            button.addEventListener('click', function(e) {
                var message = button.getAttribute('data-confirm');
                if (!confirm(message)) {
                    e.preventDefault();
                }
            });
        });
    }

    /**
     * Table sorting with keyboard accessibility.
     */
    function initTableSort() {
        var sortableHeaders = document.querySelectorAll('th[data-sort]');

        sortableHeaders.forEach(function(header) {
            header.style.cursor = 'pointer';
            header.setAttribute('tabindex', '0');
            header.setAttribute('role', 'button');
            header.setAttribute('aria-label', 'Sort by ' + header.textContent.trim());

            function handleSort() {
                var table = header.closest('table');
                var tbody = table.querySelector('tbody');
                var rows = Array.from(tbody.querySelectorAll('tr'));
                var columnIndex = Array.from(header.parentNode.children).indexOf(header);
                var sortType = header.getAttribute('data-sort');
                var isAscending = header.classList.contains('sort-asc');

                rows.sort(function(a, b) {
                    var aValue = a.children[columnIndex].textContent.trim();
                    var bValue = b.children[columnIndex].textContent.trim();

                    if (sortType === 'number') {
                        aValue = parseFloat(aValue) || 0;
                        bValue = parseFloat(bValue) || 0;
                    } else if (sortType === 'date') {
                        aValue = new Date(aValue).getTime() || 0;
                        bValue = new Date(bValue).getTime() || 0;
                    }

                    if (aValue < bValue) return isAscending ? 1 : -1;
                    if (aValue > bValue) return isAscending ? -1 : 1;
                    return 0;
                });

                // Update sort indicators and ARIA
                var headers = table.querySelectorAll('th[data-sort]');
                headers.forEach(function(h) {
                    h.classList.remove('sort-asc', 'sort-desc');
                    h.removeAttribute('aria-sort');
                });

                var newDirection = isAscending ? 'desc' : 'asc';
                header.classList.add('sort-' + newDirection);
                header.setAttribute('aria-sort', newDirection === 'asc' ? 'ascending' : 'descending');

                // Reorder rows
                rows.forEach(function(row) {
                    tbody.appendChild(row);
                });

                announce('Table sorted by ' + header.textContent.trim() + ' ' + (newDirection === 'asc' ? 'ascending' : 'descending'));
            }

            header.addEventListener('click', handleSort);
            header.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSort();
                }
            });
        });
    }

    /**
     * Dropdown navigation with full keyboard and ARIA support.
     */
    function initDropdownNavigation() {
        var dropdowns = document.querySelectorAll('.nav-dropdown');
        var dropdownIdCounter = 0;

        dropdowns.forEach(function(dropdown) {
            var trigger = dropdown.querySelector('.nav-link');
            var content = dropdown.querySelector('.nav-dropdown__content, .dropdown-content');

            if (!trigger || !content) return;

            // Generate unique IDs for ARIA relationships
            var menuId = 'nav-dropdown-menu-' + dropdownIdCounter;
            dropdownIdCounter++;

            // Set up ARIA attributes
            content.setAttribute('id', menuId);
            content.setAttribute('role', 'menu');
            content.setAttribute('aria-hidden', 'true');
            trigger.setAttribute('aria-haspopup', 'menu');
            trigger.setAttribute('aria-expanded', 'false');
            trigger.setAttribute('aria-controls', menuId);

            // Set role on menu items
            var links = content.querySelectorAll('a');
            links.forEach(function(link) {
                link.setAttribute('role', 'menuitem');
                link.setAttribute('tabindex', '-1');
            });

            /**
             * Open the dropdown menu.
             */
            function openDropdown() {
                dropdown.classList.add('nav-dropdown--open');
                trigger.setAttribute('aria-expanded', 'true');
                content.setAttribute('aria-hidden', 'false');
                // Make menu items focusable
                links.forEach(function(link) {
                    link.setAttribute('tabindex', '0');
                });
            }

            /**
             * Close the dropdown menu.
             */
            function closeDropdown() {
                dropdown.classList.remove('nav-dropdown--open');
                trigger.setAttribute('aria-expanded', 'false');
                content.setAttribute('aria-hidden', 'true');
                // Make menu items non-focusable
                links.forEach(function(link) {
                    link.setAttribute('tabindex', '-1');
                });
            }

            /**
             * Toggle the dropdown menu.
             */
            function toggleDropdown() {
                var isOpen = trigger.getAttribute('aria-expanded') === 'true';
                if (isOpen) {
                    closeDropdown();
                } else {
                    // Close other open dropdowns first
                    document.querySelectorAll('.nav-dropdown--open').forEach(function(openDropdown) {
                        var openTrigger = openDropdown.querySelector('.nav-link');
                        var openContent = openDropdown.querySelector('.nav-dropdown__content, .dropdown-content');
                        if (openTrigger && openContent) {
                            openDropdown.classList.remove('nav-dropdown--open');
                            openTrigger.setAttribute('aria-expanded', 'false');
                            openContent.setAttribute('aria-hidden', 'true');
                        }
                    });
                    openDropdown();
                }
            }

            // Keyboard navigation on trigger
            trigger.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleDropdown();
                    if (trigger.getAttribute('aria-expanded') === 'true') {
                        var firstLink = content.querySelector('a');
                        if (firstLink) {
                            firstLink.focus();
                        }
                    }
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    openDropdown();
                    var firstLink = content.querySelector('a');
                    if (firstLink) {
                        firstLink.focus();
                    }
                } else if (e.key === 'Escape') {
                    closeDropdown();
                }
            });

            // Navigate within dropdown
            links.forEach(function(link, index) {
                link.addEventListener('keydown', function(e) {
                    if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        if (links[index + 1]) {
                            links[index + 1].focus();
                        } else {
                            // Wrap to first item
                            links[0].focus();
                        }
                    } else if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        if (index > 0) {
                            links[index - 1].focus();
                        } else {
                            // Wrap to last item or go back to trigger
                            trigger.focus();
                        }
                    } else if (e.key === 'Escape') {
                        closeDropdown();
                        trigger.focus();
                    } else if (e.key === 'Tab') {
                        // Allow tab to naturally move focus, close dropdown
                        closeDropdown();
                    }
                });
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {
                if (!dropdown.contains(e.target)) {
                    closeDropdown();
                }
            });

            // Support hover for mouse users (preserve existing behavior)
            dropdown.addEventListener('mouseenter', function() {
                openDropdown();
            });

            dropdown.addEventListener('mouseleave', function() {
                closeDropdown();
            });
        });
    }

    /**
     * Announce message to screen readers via live region.
     * @param {string} message - Message to announce
     * @param {string} priority - 'polite' (default) or 'assertive'
     */
    function announce(message, priority) {
        var liveRegion = document.getElementById('live-region');
        if (!liveRegion) {
            liveRegion = document.createElement('div');
            liveRegion.id = 'live-region';
            liveRegion.className = 'live-region';
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            document.body.appendChild(liveRegion);
        }

        if (priority === 'assertive') {
            liveRegion.setAttribute('aria-live', 'assertive');
        } else {
            liveRegion.setAttribute('aria-live', 'polite');
        }

        // Clear and set message (required for some screen readers)
        liveRegion.textContent = '';
        setTimeout(function() {
            liveRegion.textContent = message;
        }, 100);
    }

    /**
     * Show a temporary alert message.
     * @param {string} message - Alert message
     * @param {string} type - Alert type (success, danger, warning, info)
     */
    function showAlert(message, type) {
        var container = document.querySelector('.flash-messages');
        if (!container) {
            container = document.createElement('div');
            container.className = 'flash-messages';
            container.setAttribute('role', 'alert');
            container.setAttribute('aria-live', 'polite');
            var main = document.querySelector('main');
            if (main) {
                main.insertBefore(container, main.firstChild);
            }
        }

        var alert = document.createElement('div');
        alert.className = 'alert alert-' + type;
        alert.innerHTML = '<span>' + escapeHtml(message) + '</span>' +
            '<button type="button" class="alert__close" aria-label="Dismiss message">' +
            '<span aria-hidden="true">&times;</span></button>';

        alert.querySelector('.alert__close').addEventListener('click', function() {
            alert.remove();
        });

        container.appendChild(alert);

        // Announce to screen readers
        announce(message);

        // Auto-dismiss after 5 seconds
        setTimeout(function() {
            if (alert.parentNode) {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.3s ease';
                setTimeout(function() {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 300);
            }
        }, 5000);
    }

    /**
     * Escape HTML to prevent XSS.
     * @param {string} text - Text to escape
     * @returns {string} Escaped HTML
     */
    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Expose utilities globally for use in templates
    window.showAlert = showAlert;
    window.announce = announce;

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
