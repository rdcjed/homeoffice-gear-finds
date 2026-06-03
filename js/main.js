// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.querySelector('.mobile-menu-toggle');
    const navMenu = document.querySelector('.main-nav ul');
    if (toggle && navMenu) {
        toggle.addEventListener('click', function() {
            navMenu.classList.toggle('open');
        });
    }

    // Load articles from JSON (for homepage listing)
    const postGrid = document.getElementById('post-grid');
    if (postGrid) {
        fetch('/homeoffice-gear-finds/articles/articles.json')
            .then(r => r.json())
            .then(articles => {
                postGrid.innerHTML = articles.map(a => `
                    <article class="post-card">
                        <div class="post-card-image">${a.emoji}</div>
                        <div class="post-card-body">
                            <span class="post-card-category">${a.category}</span>
                            <h3><a href="/homeoffice-gear-finds/${a.url}">${a.title}</a></h3>
                            <p>${a.excerpt}</p>
                            <div class="post-card-meta">
                                <span>${a.date}</span>
                                <a href="/homeoffice-gear-finds/${a.url}" class="read-more">Read Review →</a>
                            </div>
                        </div>
                    </article>
                `).join('');
            });
    }
});