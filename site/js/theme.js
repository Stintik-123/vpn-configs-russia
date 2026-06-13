// site/js/theme.js — простой переключатель темы
(function() {
    const storageKey = 'vpn_theme';
    const getCurrentTheme = () => localStorage.getItem(storageKey) || 'dark';
    
    function applyTheme(theme) {
        const root = document.documentElement;
        if (theme === 'light') {
            root.style.setProperty('--bg', '#F5F5F7');
            root.style.setProperty('--card', '#FFFFFF');
            root.style.setProperty('--border', '#DDDDDD');
            root.style.setProperty('--text', '#000000');
            root.style.setProperty('--text-dim', '#555555');
            root.style.setProperty('--accent', '#000000');
            root.style.setProperty('--accent-hover', '#333333');
        } else {
            root.style.setProperty('--bg', '#0A0A0A');
            root.style.setProperty('--card', '#111111');
            root.style.setProperty('--border', '#222222');
            root.style.setProperty('--text', '#FFFFFF');
            root.style.setProperty('--text-dim', '#888888');
            root.style.setProperty('--accent', '#FFFFFF');
            root.style.setProperty('--accent-hover', '#CCCCCC');
        }
        localStorage.setItem(storageKey, theme);
    }
    
    function createToggleButton() {
        const btn = document.createElement('button');
        btn.className = 'theme-toggle';
        btn.innerHTML = '🌙 Светлая тема';
        const current = getCurrentTheme();
        btn.innerHTML = current === 'dark' ? '☀️ Светлая тема' : '🌙 Тёмная тема';
        btn.onclick = () => {
            const newTheme = getCurrentTheme() === 'dark' ? 'light' : 'dark';
            applyTheme(newTheme);
            btn.innerHTML = newTheme === 'dark' ? '☀️ Светлая тема' : '🌙 Тёмная тема';
        };
        document.body.appendChild(btn);
    }
    
    // применяем сохранённую тему
    applyTheme(getCurrentTheme());
    window.addEventListener('DOMContentLoaded', createToggleButton);
})();
