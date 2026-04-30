document.addEventListener('DOMContentLoaded', () => {
    // 导航切换
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.section');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            sections.forEach(section => section.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');
        });
    });

    // 职业选择切换
    const classBtns = document.querySelectorAll('.class-btn');
    const classContents = document.querySelectorAll('.class-content');

    classBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetClass = btn.getAttribute('data-class');
            
            classBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            classContents.forEach(content => content.classList.remove('active'));
            document.getElementById(targetClass).classList.add('active');
        });
    });

    // 装备标签切换
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // 添加悬停效果动画
    const skillItems = document.querySelectorAll('.skill-category li');
    skillItems.forEach(item => {
        item.addEventListener('mouseenter', () => {
            item.style.transform = 'translateX(5px)';
            item.style.transition = 'transform 0.2s ease';
        });
        item.addEventListener('mouseleave', () => {
            item.style.transform = 'translateX(0)';
        });
    });

    // 添加装备卡片悬停效果
    const equipmentCards = document.querySelectorAll('.equipment-card');
    equipmentCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-5px)';
            card.style.transition = 'transform 0.3s ease';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });
    });

    // 添加攻略部分展开/收起功能
    const actGuides = document.querySelectorAll('.act-guide');
    actGuides.forEach(guide => {
        const header = guide.querySelector('h3');
        const content = guide.querySelector('.guide-section');
        
        header.style.cursor = 'pointer';
        header.addEventListener('click', () => {
            const sections = guide.querySelectorAll('.guide-section');
            sections.forEach(section => {
                section.style.display = section.style.display === 'none' ? 'block' : 'none';
            });
        });
    });
});