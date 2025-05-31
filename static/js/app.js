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

function showSuggestions() {
    const field = document.getElementById('searchField').value;
    const suggestions = recentSearches[field] || [];
    const container = document.getElementById('suggestions');
    
    if (suggestions.length === 0) {
        hideSuggestions();
        return;
    }
    
    container.innerHTML = suggestions.map(s => 
        `<div class="suggestion" onclick="selectSuggestion('${s}')">
            <span>🕒</span> ${s}
        </div>`
    ).join('');
    container.style.display = 'block';
}

function hideSuggestions() {
    document.getElementById('suggestions').style.display = 'none';
}

function filterSuggestions() {
    const input = document.getElementById('searchInput').value.toLowerCase();
    const field = document.getElementById('searchField').value;
    const suggestions = (recentSearches[field] || []).filter(s => s.toLowerCase().includes(input));
    const container = document.getElementById('suggestions');
    
    if (suggestions.length === 0 || input === '') {
        hideSuggestions();
        return;
    }
    
    container.innerHTML = suggestions.map(s => 
        `<div class="suggestion" onclick="selectSuggestion('${s}')">
            <span>🕒</span> ${s}
        </div>`
    ).join('');
    container.style.display = 'block';
}

function selectSuggestion(value) {
    document.getElementById('searchInput').value = value;
    hideSuggestions();
    search();
}

function toggleFilters() {
    const section = document.getElementById('filterSection');
    const btn = document.getElementById('filterBtn');
    const isVisible = section.style.display === 'block';
    section.style.display = isVisible ? 'none' : 'block';
    btn.classList.toggle('active', !isVisible);
}

function updateFilterChips() {
    const comunidad = document.getElementById('comunidadFilter').value;
    const estado = document.getElementById('estadoFilter').value;
    const container = document.getElementById('filterChips');
    
    let chips = '';
    if (comunidad) chips += `<div class="chip">Comunidad: ${comunidad} <span class="close" onclick="clearFilter('comunidad')">✕</span></div>`;
    if (estado) chips += `<div class="chip">Estado: ${estado} <span class="close" onclick="clearFilter('estado')">✕</span></div>`;
    
    container.innerHTML = chips;
}

function clearFilter(type) {
    if (type === 'comunidad') document.getElementById('comunidadFilter').value = '';
    if (type === 'estado') document.getElementById('estadoFilter').value = '';
    updateFilterChips();
}

function getEstadoStyle(estado) {
    const styles = {
        'caracterizado': { bg: 'rgba(149, 75, 151, 0.1)', color: '#954B97' },
        'encuestado': { bg: 'rgba(0, 146, 221, 0.1)', color: '#0092DD' },
        'preasignado': { bg: 'rgba(253, 197, 51, 0.1)', color: '#fdc533' },
        'asignado': { bg: 'rgba(47, 172, 102, 0.1)', color: '#2fac66' },
        'inactivo': { bg: 'rgba(233, 67, 98, 0.1)', color: '#e94362' }
    };
    return styles[estado?.toLowerCase()] || { bg: '#f0f0f0', color: '#333' };
}

async function search() {
    const field = document.getElementById('searchField').value;
    const value = document.getElementById('searchInput').value.trim();
    const comunidad = document.getElementById('comunidadFilter').value;
    const estado = document.getElementById('estadoFilter').value;
    
    if (!value) return;
    
    const container = document.getElementById('results');
    container.innerHTML = '<div style="text-align:center;padding:2rem;">Buscando...</div>';
    
    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                field, value,
                filters: { comunidad, estado }
            })
        });
        
        const data = await response.json();
        currentResults = data.results;
        displayResults();
    } catch (error) {
        container.innerHTML = '<div style="color:red;text-align:center;padding:2rem;">Error en la búsqueda</div>';
    }
}

function displayResults() {
    const container = document.getElementById('results');
    
    if (currentResults.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:2rem;">No se encontraron resultados</div>';
        return;
    }
    
    if (currentResults.length === 1) {
        displaySingleResult(currentResults[0]);
        return;
    }
    
    const html = `
        <h3 style="color:#0092DD;margin-bottom:1rem;">Se encontraron ${currentResults.length} resultados:</h3>
        ${currentResults.map((result, index) => `
            <div class="result-card" onclick="selectResult(${index})">
                <div class="result-name">${result['NOMBRE COMPLETO'] || 'Sin nombre'}</div>
                <div class="result-details">
                    Comunidad: ${result['COMUNIDAD'] || 'N/A'}<br>
                    Cédula: ${result['CEDULA'] || 'N/A'}
                </div>
                <div style="text-align:right;color:#0092DD;">→</div>
            </div>
        `).join('')}
    `;
    container.innerHTML = html;
}

function selectResult(index) {
    selectedRecord = currentResults[index];
    displaySingleResult(selectedRecord);
}

function displaySingleResult(record) {
    const style = getEstadoStyle(record['ESTADO']);
    const backBtn = currentResults.length > 1 ? 
        `<button onclick="displayResults()" style="margin-bottom:1rem;padding:0.5rem 1rem;background:#ddd;border:none;border-radius:4px;">← Volver a resultados</button>` : '';
    
    const html = `
        <div class="single-result">
            ${backBtn}
            ${record['ESTADO'] ? `
                <div class="estado-badge" style="background:${style.bg};color:${style.color};">
                    ESTADO: ${record['ESTADO']}
                </div>
            ` : ''}
            <button onclick="showAddCommentDialog()" style="width:100%;margin-bottom:1rem;padding:0.75rem;background:#0092DD;color:white;border:none;border-radius:8px;font-weight:600;">
                💬 Añadir Comentario
            </button>
            ${Object.entries(record).filter(([key]) => key !== 'ESTADO').map(([key, value]) => `
                <div class="detail-row">
                    <div class="detail-label">${key}:</div>
                    <div class="detail-value">${value || '-'}</div>
                </div>
            `).join('')}
        </div>
    `;
    document.getElementById('results').innerHTML = html;
}

function showAddCommentDialog() {
    if (!selectedRecord) return;
    
    const comment = prompt('Escriba su comentario:');
    if (!comment || !comment.trim()) return;
    
    fetch('/add_comment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            record: selectedRecord,
            comment: comment.trim()
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Comentario añadido, recuerda sincronizar');
            location.reload();
        } else {
            alert('Error al guardar comentario');
        }
    })
    .catch(() => alert('Error al guardar comentario'));
}

function showCommentsDialog() {
    window.location.href = '/comments';
}

async function syncDatabase() {
    const btn = document.getElementById('syncBtn');
    btn.innerHTML = '<span class="sync-icon">🔄</span>';
    btn.style.pointerEvents = 'none';
    
    try {
        const response = await fetch('/sync_database', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            alert('Base de datos sincronizada correctamente');
            location.reload();
        } else {
            alert('Error al sincronizar');
        }
    } catch (error) {
        alert('Error al sincronizar');
    } finally {
        btn.innerHTML = '🔄';
        btn.style.pointerEvents = 'auto';
    }
}