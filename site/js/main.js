// site/js/main.js
(function() {
    // копирование ссылок
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const url = this.getAttribute('data-url');
            if (!url) return;
            navigator.clipboard.writeText(url).then(() => {
                const original = this.innerHTML;
                this.innerHTML = '✅ Скопировано!';
                setTimeout(() => { this.innerHTML = original; }, 1500);
            }).catch(() => {
                this.innerHTML = '❌ Ошибка';
                setTimeout(() => { this.innerHTML = '📋 Копировать'; }, 1500);
            });
        });
    });

    // загрузка статистики
    fetch('stats.json')
        .then(res => res.ok ? res.json() : null)
        .then(stats => {
            if (!stats) return;
            const totalEl = document.querySelector('#stats-total');
            const aliveEl = document.querySelector('#stats-alive');
            const timeEl = document.querySelector('#stats-time');
            if (totalEl) totalEl.innerText = stats.total || '—';
            if (aliveEl) aliveEl.innerText = stats.alive || '—';
            if (timeEl && stats.last_check) {
                const date = new Date(stats.last_check);
                timeEl.innerText = date.toLocaleString().slice(0, 16);
            }
        })
        .catch(() => console.log('stats.json пока не сгенерирован'));
})();
