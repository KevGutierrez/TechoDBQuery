let currentResults = [];
let selectedRecord = null;
let recentSearches = {};

document.addEventListener('DOMContentLoaded', function() {
    // Initialize recentSearches from the server-side data
    recentSearches = JSON.parse(document.getElementById('recentSearchesData').value);
    
    // Add event listeners
    document.getElementById('searchField').addEventListener('change', updatePlaceholder);
    document.getElementById('searchInput').addEventListener('focus', showSuggestions);
    document.getElementById('searchInput').addEventListener('blur', () => setTimeout(hideSuggestions, 200));
    document.getElementById('searchInput').addEventListener('input', filterSuggestions);
    document.getElementById('searchInput').addEventListener('keypress', e => e.key === 'Enter' && search());
    document.getElementById('comunidadFilter').addEventListener('change', updateFilterChips);
    document.getElementById('estadoFilter').addEventListener('change', updateFilterChips);
    
    // Initialize the page
    updatePlaceholder();
    updateFilterChips();
});

// Your existing functions here
function updatePlaceholder() {
    const field = document.getElementById('searchField').value;
    const input = document.getElementById('searchInput');
    const placeholders = {
        'CEDULA': 'Ingrese número de cédula',
        'CONTACTO 1': 'Ingrese número de celular',
        'NOMBRE COMPLETO': 'Ingrese nombre (búsqueda parcial)'
    };
    input.placeholder = placeholders[field];
    input.type = field === 'NOMBRE COMPLETO' ? 'text' : 'number';
    hideSuggestions();
}

// Add all your other existing functions here, exactly as they are in your current script