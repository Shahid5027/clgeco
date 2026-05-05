// ===== STATE =====
let currentRole = 'student';
let currentFilter = 'all';
let searchQuery = '';
let favorites = JSON.parse(localStorage.getItem('noteFavorites') || '[]');
let recentlyViewed = JSON.parse(localStorage.getItem('noteRecent') || '[]');
let lastDeletedNote = null;
let undoToastTimer = null;

// ===== MOCK DATA =====
const subjectClass = { 'Mathematics':'subject-math','Science':'subject-science','English':'subject-english','History':'subject-history','Computer Science':'subject-cs' };

let notesData = [
  { id:1, title:"Introduction to Calculus", subject:"Mathematics", author:"Dr. Sharma", date:"2026-04-28",
    preview:"Calculus is the mathematical study of continuous change. It has two major branches: differential calculus and integral calculus.",
    content:`<h2>What is Calculus?</h2><p>Calculus is the mathematical study of continuous change, in the same way that geometry is the study of shape and algebra is the study of generalizations of arithmetic operations.</p><h2>Two Major Branches</h2><p><strong>Differential Calculus</strong> concerns the study of rates at which quantities change. The derivative of a function measures the sensitivity to change of the output value with respect to a change in its input value.</p><p><strong>Integral Calculus</strong> concerns accumulation of quantities and the areas under and between curves. The definite integral of a function can be interpreted as the signed area of the region bounded by its graph.</p><h3>Key Concepts</h3><ul><li>Limits and Continuity</li><li>Derivatives and Differentiation Rules</li><li>Applications of Derivatives</li><li>Integrals and Integration Techniques</li></ul><blockquote>Calculus was independently developed by Isaac Newton and Gottfried Wilhelm Leibniz in the late 17th century.</blockquote><p>Understanding calculus is essential for advanced studies in mathematics, physics, engineering, economics, and many other fields.</p>`,
    summary:"Calculus studies continuous change via two branches: differential (rates of change, derivatives) and integral (accumulation, areas). Key concepts include limits, differentiation rules, and integration techniques. Developed by Newton and Leibniz.",
    explanation:"Think of calculus like measuring a road trip. Differential calculus is your speedometer—it tells you how fast you're going at any moment. Integral calculus is your odometer—it tells you the total distance traveled. Together they help us understand anything that changes continuously." },
  { id:2, title:"Photosynthesis: The Complete Process", subject:"Science", author:"Prof. Mehta", date:"2026-04-25",
    preview:"Photosynthesis is the process by which green plants convert sunlight into chemical energy stored in glucose molecules.",
    content:`<h2>Overview of Photosynthesis</h2><p>Photosynthesis is a process used by plants, algae, and certain bacteria to convert light energy into chemical energy stored in glucose. This process is fundamental to life on Earth.</p><h2>The Chemical Equation</h2><p><code>6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂</code></p><h2>Two Stages</h2><h3>Light-Dependent Reactions</h3><p>These occur in the thylakoid membranes of chloroplasts. Water molecules are split, oxygen is released, and energy carriers ATP and NADPH are produced.</p><h3>Calvin Cycle (Light-Independent)</h3><p>These reactions take place in the stroma. CO₂ is fixed into organic molecules using the ATP and NADPH produced in the light reactions.</p><ul><li>Carbon fixation by RuBisCO enzyme</li><li>Reduction phase producing G3P</li><li>Regeneration of RuBP</li></ul><blockquote>Without photosynthesis, the oxygen in our atmosphere would be depleted within several thousand years.</blockquote>`,
    summary:"Photosynthesis converts sunlight, CO₂, and water into glucose and oxygen via two stages: light-dependent reactions (in thylakoids, producing ATP/NADPH) and the Calvin Cycle (in stroma, fixing carbon into glucose).",
    explanation:"Imagine photosynthesis as a tiny solar-powered kitchen inside each leaf. Sunlight is the electricity, water and CO₂ are the raw ingredients, and glucose is the meal that feeds the plant. Oxygen? That's just the cooking exhaust released into the air for us to breathe!" },
  { id:3, title:"Shakespeare's Literary Techniques", subject:"English", author:"Dr. Iyer", date:"2026-04-22",
    preview:"An exploration of the dramatic and poetic techniques employed by William Shakespeare across his most celebrated works.",
    content:`<h2>Shakespeare's Craft</h2><p>William Shakespeare employed a wide range of literary techniques that made his works timeless. His mastery of language, character development, and dramatic structure continues to influence literature today.</p><h2>Key Techniques</h2><h3>Soliloquy</h3><p>Characters speak their inner thoughts aloud, giving the audience direct access to their psychology. Hamlet's "To be, or not to be" is the most famous example.</p><h3>Dramatic Irony</h3><p>The audience knows something the characters don't. In Romeo and Juliet, we know Juliet is alive while Romeo believes she's dead.</p><h3>Iambic Pentameter</h3><p>Shakespeare wrote most of his plays in unrhymed iambic pentameter (blank verse), creating a natural rhythm that mirrors English speech patterns.</p><ul><li>Metaphor and Simile</li><li>Foreshadowing</li><li>Comic Relief</li><li>Wordplay and Puns</li></ul><blockquote>"All the world's a stage, and all the men and women merely players." — As You Like It</blockquote>`,
    summary:"Shakespeare used soliloquy for inner thoughts, dramatic irony for tension, and iambic pentameter for natural rhythm. Other techniques include metaphor, foreshadowing, comic relief, and extensive wordplay.",
    explanation:"Shakespeare was like a master chef of words. Soliloquies are when a character 'thinks out loud' so you hear their secrets. Dramatic irony is when YOU know something the character doesn't—like watching a horror movie and wanting to yell 'Don't open that door!'" },
  { id:4, title:"World War II: Causes and Impact", subject:"History", author:"Prof. Khan", date:"2026-04-20",
    preview:"A comprehensive analysis of the political, economic, and social factors that led to World War II and its lasting global impact.",
    content:`<h2>Causes of World War II</h2><p>World War II (1939-1945) was the deadliest conflict in human history. Multiple interconnected factors led to its outbreak.</p><h3>Treaty of Versailles</h3><p>The harsh terms imposed on Germany after WWI created economic hardship and national resentment, providing fertile ground for extremist ideologies.</p><h3>Rise of Fascism</h3><p>Adolf Hitler's Nazi Party gained power by exploiting economic despair and nationalist sentiment. Similar authoritarian regimes arose in Italy and Japan.</p><h2>Global Impact</h2><ul><li>Estimated 70-85 million deaths</li><li>Formation of the United Nations</li><li>Beginning of the Cold War</li><li>Decolonization movements across Asia and Africa</li><li>Creation of the Universal Declaration of Human Rights</li></ul><blockquote>The war fundamentally reshaped the global political order, transitioning power from European empires to the United States and Soviet Union.</blockquote>`,
    summary:"WWII was caused by the Treaty of Versailles aftermath, rise of fascism, and failure of appeasement. Its impact: 70-85M deaths, UN formation, Cold War beginning, decolonization, and the Universal Declaration of Human Rights.",
    explanation:"Think of WWII like a pressure cooker. WWI's unfair peace treaty was the heat, economic depression added more pressure, and fascist leaders like Hitler were the spark. When it finally exploded, it changed the entire world map and led to new organizations like the UN to prevent it from happening again." },
  { id:5, title:"Data Structures: Arrays and Linked Lists", subject:"Computer Science", author:"Dr. Patel", date:"2026-04-18",
    preview:"A fundamental comparison of arrays and linked lists, two of the most essential data structures in computer science.",
    content:`<h2>Arrays</h2><p>An array is a collection of elements stored at contiguous memory locations. Elements can be accessed directly by their index, providing O(1) access time.</p><h3>Advantages</h3><ul><li>Fast random access — O(1)</li><li>Cache-friendly due to contiguous memory</li><li>Simple implementation</li></ul><h3>Disadvantages</h3><ul><li>Fixed size (in many languages)</li><li>Expensive insertions and deletions — O(n)</li></ul><h2>Linked Lists</h2><p>A linked list consists of nodes where each node contains data and a reference to the next node. They allow efficient insertions and deletions.</p><h3>Advantages</h3><ul><li>Dynamic size</li><li>Efficient insertions/deletions — O(1) at known position</li></ul><h3>Disadvantages</h3><ul><li>No random access — O(n) traversal</li><li>Extra memory for pointers</li></ul><blockquote>Choosing between arrays and linked lists depends on your specific use case: frequent access favors arrays, frequent modifications favor linked lists.</blockquote>`,
    summary:"Arrays offer O(1) access via contiguous memory but costly O(n) insertions. Linked lists provide dynamic sizing and O(1) insertions at known positions but require O(n) traversal. Choice depends on access vs modification frequency.",
    explanation:"Arrays are like a row of lockers in school — each has a number, and you can go directly to locker #5. But if you want to add a new locker in the middle, everyone has to shift over. Linked lists are like a scavenger hunt — each clue points to the next location. Easy to add new clues anywhere, but you have to follow the chain to find a specific one." },
  { id:6, title:"Organic Chemistry: Functional Groups", subject:"Science", author:"Dr. Reddy", date:"2026-04-15",
    preview:"Understanding functional groups is key to predicting the behavior of organic compounds in chemical reactions.",
    content:`<h2>What Are Functional Groups?</h2><p>Functional groups are specific groupings of atoms within molecules that determine the characteristics of the molecule. They are the centers of chemical reactivity.</p><h2>Common Functional Groups</h2><h3>Hydroxyl Group (-OH)</h3><p>Found in alcohols. Makes molecules polar and capable of forming hydrogen bonds, increasing solubility in water.</p><h3>Carbonyl Group (C=O)</h3><p>Found in aldehydes and ketones. Highly reactive due to the polar nature of the C=O bond.</p><h3>Carboxyl Group (-COOH)</h3><p>Found in carboxylic acids. Can donate a proton (H⁺), making the molecule acidic.</p><h3>Amino Group (-NH₂)</h3><p>Found in amines and amino acids. Can accept a proton, making the molecule basic.</p><blockquote>Functional groups allow chemists to predict and classify the reactivity of millions of organic compounds using a relatively small set of rules.</blockquote>`,
    summary:"Functional groups are atom clusters determining molecular behavior. Key groups: Hydroxyl (-OH) in alcohols, Carbonyl (C=O) in aldehydes/ketones, Carboxyl (-COOH) in acids, and Amino (-NH₂) in amines. They enable prediction of chemical reactivity.",
    explanation:"Think of functional groups as 'personality badges' on molecules. Just like seeing a firefighter's badge tells you what they do, seeing an -OH group tells you the molecule will mix well with water. Each badge gives the molecule specific 'superpowers' — acids can donate protons, bases can accept them." },
  { id:7, title:"Linear Algebra: Matrices and Vectors", subject:"Mathematics", author:"Dr. Sharma", date:"2026-04-12",
    preview:"Matrices and vectors form the foundation of linear algebra, essential for computer graphics, machine learning, and engineering.",
    content:`<h2>Vectors</h2><p>A vector is a quantity with both magnitude and direction. In linear algebra, vectors are represented as ordered lists of numbers. A vector in ℝⁿ has n components.</p><h2>Matrices</h2><p>A matrix is a rectangular array of numbers arranged in rows and columns. An m×n matrix has m rows and n columns.</p><h3>Matrix Operations</h3><ul><li><strong>Addition:</strong> Element-wise addition of same-sized matrices</li><li><strong>Scalar Multiplication:</strong> Multiply every element by a scalar</li><li><strong>Matrix Multiplication:</strong> Row-by-column dot products</li><li><strong>Transpose:</strong> Swap rows and columns</li></ul><h3>Applications</h3><ul><li>Computer Graphics and 3D Transformations</li><li>Machine Learning and Neural Networks</li><li>Solving Systems of Linear Equations</li><li>Quantum Mechanics</li></ul><blockquote>Linear algebra is the mathematics of data. Nearly every modern algorithm in AI and machine learning relies on matrix and vector operations.</blockquote>`,
    summary:"Vectors are ordered number lists with magnitude/direction. Matrices are rectangular number arrays. Key operations: addition, scalar multiplication, matrix multiplication, transpose. Used in computer graphics, ML, physics, and solving equation systems.",
    explanation:"Imagine vectors as arrows pointing somewhere on a map. Matrices are like transformation machines — feed an arrow in, and the matrix stretches, rotates, or flips it. In video games, every time a 3D character moves or rotates, matrices are doing the math behind the scenes!" },
  { id:8, title:"The Renaissance Period", subject:"History", author:"Prof. Khan", date:"2026-04-10",
    preview:"The Renaissance was a cultural movement that profoundly affected European intellectual life, spanning from the 14th to 17th century.",
    content:`<h2>What Was the Renaissance?</h2><p>The Renaissance (14th–17th century) was a period of cultural, artistic, political, and economic rebirth following the Middle Ages. It began in Italy and gradually spread across Europe.</p><h2>Key Characteristics</h2><h3>Humanism</h3><p>A philosophical movement emphasizing human potential and achievements. Scholars studied classical Greek and Roman texts, shifting focus from purely religious subjects.</p><h3>Art and Innovation</h3><p>Artists like Leonardo da Vinci, Michelangelo, and Raphael revolutionized art with techniques like perspective, chiaroscuro, and anatomical accuracy.</p><h3>Scientific Revolution</h3><p>Thinkers like Galileo, Copernicus, and Kepler challenged traditional views with empirical observation and the scientific method.</p><ul><li>Invention of the printing press by Gutenberg</li><li>Exploration and discovery of new trade routes</li><li>Rise of merchant classes and banking</li></ul><blockquote>The Renaissance laid the intellectual groundwork for the modern Western world, bridging the medieval and modern eras.</blockquote>`,
    summary:"The Renaissance (14th-17th century) was a European cultural rebirth emphasizing humanism, artistic innovation (da Vinci, Michelangelo), and scientific revolution (Galileo, Copernicus). Key developments: printing press, exploration, rise of merchant classes.",
    explanation:"The Renaissance was like Europe 'waking up' after a long nap. People rediscovered ancient Greek and Roman ideas, artists started painting realistic humans instead of flat figures, and scientists began questioning 'because the Church says so' with 'let me test that.' It was the original 'glow up' of Western civilization!" }
];

// ===== QUIZ DATA =====
const quizzes = {
  'Mathematics': [
    { q:"What is the derivative of x²?", opts:["x","2x","x²","2"], ans:1 },
    { q:"What does an integral calculate?", opts:["Rate of change","Area under curve","Slope","Maximum value"], ans:1 },
    { q:"Who co-developed calculus?", opts:["Einstein","Euler","Newton","Archimedes"], ans:2 }
  ],
  'Science': [
    { q:"What is the byproduct of photosynthesis?", opts:["CO₂","Nitrogen","Oxygen","Hydrogen"], ans:2 },
    { q:"Where do light reactions occur?", opts:["Stroma","Nucleus","Thylakoids","Cytoplasm"], ans:2 },
    { q:"What does -OH represent?", opts:["Amino group","Hydroxyl group","Carbonyl group","Carboxyl group"], ans:1 }
  ],
  'English': [
    { q:"What is a soliloquy?", opts:["A song","Speaking thoughts aloud","A letter","A type of poem"], ans:1 },
    { q:"What meter did Shakespeare primarily use?", opts:["Trochaic","Iambic pentameter","Free verse","Alexandrine"], ans:1 },
    { q:"Dramatic irony is when...", opts:["Characters lie","Audience knows more than characters","A joke is told","The plot twists"], ans:1 }
  ],
  'History': [
    { q:"When did WWII begin?", opts:["1935","1939","1941","1945"], ans:1 },
    { q:"The Renaissance began in which country?", opts:["France","England","Germany","Italy"], ans:3 },
    { q:"What did Gutenberg invent?", opts:["Telescope","Compass","Printing press","Steam engine"], ans:2 }
  ],
  'Computer Science': [
    { q:"Array access time complexity?", opts:["O(n)","O(log n)","O(1)","O(n²)"], ans:2 },
    { q:"Linked list advantage over arrays?", opts:["Faster access","Dynamic size","Less memory","Simpler code"], ans:1 },
    { q:"What is a matrix?", opts:["A single number","A rectangular array of numbers","A type of graph","A linked list"], ans:1 }
  ]
};

// ===== HELPERS =====
function getSubjectClass(s) { return subjectClass[s] || 'subject-default'; }
function showToast(msg, actionLabel, actionCallback) {
  const t = document.getElementById('toast');
  clearTimeout(undoToastTimer);
  t.innerHTML = `<span>${msg}</span>`;

  if (actionLabel && actionCallback) {
    const button = document.createElement('button');
    button.className = 'toast-action';
    button.textContent = actionLabel;
    button.onclick = () => {
      actionCallback();
      t.classList.remove('show');
    };
    t.appendChild(button);
  }

  t.classList.add('show');
  undoToastTimer = setTimeout(() => t.classList.remove('show'), 2500);
}

// ===== ROLE TOGGLE =====
function toggleRole() {
  currentRole = currentRole === 'student' ? 'teacher' : 'student';
  const badge = document.getElementById('role-badge');
  const btn = document.getElementById('role-toggle');
  const fab = document.getElementById('fab-btn');
  badge.textContent = currentRole === 'student' ? 'Student' : 'Teacher';
  badge.className = 'role-badge ' + currentRole;
  btn.textContent = currentRole === 'student' ? 'Switch to Teacher' : 'Switch to Student';
  fab.style.display = currentRole === 'teacher' ? 'flex' : 'none';
  renderNotes();
}

// ===== FILTERING & SEARCH =====
function setFilter(filter, el) {
  currentFilter = filter;
  document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  renderNotes();
}
function handleSearch() {
  searchQuery = document.getElementById('search-input').value.toLowerCase();
  renderNotes();
}
function getFilteredNotes() {
  let notes = [...notesData];
  if (searchQuery) notes = notes.filter(n => n.title.toLowerCase().includes(searchQuery) || n.subject.toLowerCase().includes(searchQuery));
  if (currentFilter === 'favorites') notes = notes.filter(n => favorites.includes(n.id));
  else if (currentFilter === 'recent') notes.sort((a,b) => new Date(b.date) - new Date(a.date));
  else if (currentFilter !== 'all') notes = notes.filter(n => n.subject === currentFilter);
  return notes;
}

// ===== RENDER NOTES =====
function renderNotes() {
  const grid = document.getElementById('notes-grid');
  const empty = document.getElementById('empty-state');
  const filtered = getFilteredNotes();
  if (!filtered.length) { grid.innerHTML = ''; empty.style.display = 'block'; return; }
  empty.style.display = 'none';
  grid.innerHTML = filtered.map(n => `
    <div class="note-card" onclick="openNote(${n.id})">
      <div class="note-card-header">
        <span class="note-card-subject ${getSubjectClass(n.subject)}">${n.subject}</span>
        <button class="favorite-btn ${favorites.includes(n.id)?'active':''}" onclick="event.stopPropagation();toggleFav(${n.id})">
          ${favorites.includes(n.id)?'★':'☆'}
        </button>
      </div>
      <h3 class="note-card-title">${n.title}</h3>
      <p class="note-card-preview">${n.preview}</p>
      <div class="note-card-footer">
        <span class="note-card-date">📅 ${formatDate(n.date)}</span>
        <span class="note-card-author"><span class="author-avatar">${n.author[0]}</span>${n.author}</span>
      </div>
      ${n.file ? `<div class="note-file-tag">📎 ${n.file.name}</div>` : ''}
      ${currentRole==='teacher'?`<div class="card-actions">
        <button class="card-action-btn" onclick="event.stopPropagation();editNote(${n.id})">✏️ Edit</button>
        <button class="card-action-btn delete" onclick="event.stopPropagation();deleteNote(${n.id})">🗑️ Delete</button>
      </div>`:''}
    </div>
  `).join('');
  renderRecent();
}

function formatDate(d) {
  return new Date(d).toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' });
}

// ===== RECENTLY VIEWED =====
function renderRecent() {
  const sec = document.getElementById('recent-section');
  const scroll = document.getElementById('recent-scroll');
  if (!recentlyViewed.length) { sec.style.display = 'none'; return; }
  sec.style.display = 'block';
  const recents = recentlyViewed.map(id => notesData.find(n => n.id === id)).filter(Boolean).slice(0,6);
  if (!recents.length) { sec.style.display = 'none'; return; }
  scroll.innerHTML = recents.map(n => `
    <div class="recent-card" onclick="openNote(${n.id})">
      <div class="recent-card-title">${n.title}</div>
      <div class="recent-card-meta">${n.subject} · ${formatDate(n.date)}</div>
    </div>
  `).join('');
}

function clearRecentlyViewed() {
  recentlyViewed = [];
  localStorage.removeItem('noteRecent');
  renderNotes();
  showToast('Recently viewed cleared');
}

// ===== FAVORITES =====
function toggleFav(id) {
  const i = favorites.indexOf(id);
  if (i > -1) { favorites.splice(i,1); showToast('Removed from favorites'); }
  else { favorites.push(id); showToast('Added to favorites ⭐'); }
  localStorage.setItem('noteFavorites', JSON.stringify(favorites));
  renderNotes();
}

// ===== OPEN NOTE DETAIL =====
function openNote(id) {
  const note = notesData.find(n => n.id === id);
  if (!note) return;
  // Track recently viewed
  recentlyViewed = recentlyViewed.filter(r => r !== id);
  recentlyViewed.unshift(id);
  if (recentlyViewed.length > 10) recentlyViewed.pop();
  localStorage.setItem('noteRecent', JSON.stringify(recentlyViewed));

  const detail = document.getElementById('detail-view');
  const content = document.getElementById('detail-content');
  const actions = document.getElementById('detail-actions');

  content.innerHTML = `
    <span class="detail-subject-badge ${getSubjectClass(note.subject)}">${note.subject}</span>
    <h1 class="detail-title">${note.title}</h1>
    <div class="detail-meta">
      <span>By ${note.author}</span>
      <span>·</span>
      <span>${formatDate(note.date)}</span>
    </div>
    <div class="detail-body">${note.content}</div>
    ${note.file ? `
      <div class="detail-file-box">
        <div class="detail-file-name">📎 ${note.file.name}</div>
        <div class="detail-file-actions">
          <a class="detail-file-link" href="${note.file.url}" target="_blank" rel="noopener">Open</a>
          <a class="detail-file-link download" href="${note.file.url}" download="${note.file.name}">Download</a>
        </div>
        ${note.file.type === 'application/pdf' ? `<iframe class="note-pdf-preview" src="${note.file.url}"></iframe>` : ''}
      </div>
    ` : ''}
    <div id="ai-container"></div>
  `;

  actions.innerHTML = `
    <button class="detail-action-btn" onclick="toggleFav(${note.id});openNote(${note.id})">
      ${favorites.includes(note.id)?'★':'☆'} ${favorites.includes(note.id)?'Favorited':'Favorite'}
    </button>
    <button class="detail-action-btn accent-btn" onclick="showSummary(${note.id})">✨ Summarize</button>
    <button class="detail-action-btn" onclick="showExplanation(${note.id})">💡 Explain</button>
    <button class="detail-action-btn" onclick="openQuiz('${note.subject}')">📝 Quiz</button>
  `;

  detail.classList.add('active');
  detail.scrollTop = 0;
}

function closeDetail() {
  document.getElementById('detail-view').classList.remove('active');
  renderNotes();
}

// ===== AI FEATURES =====
function showSummary(id) {
  const note = notesData.find(n => n.id === id);
  const container = document.getElementById('ai-container');
  container.innerHTML = `<div class="ai-panel"><div class="ai-panel-header"><div class="ai-icon">✨</div><div class="ai-panel-title">AI Summary</div></div><div class="ai-panel-body"><div class="ai-typing"><span></span><span></span><span></span></div></div></div>`;
  setTimeout(() => {
    container.querySelector('.ai-panel-body').innerHTML = `<p>${note.summary}</p>`;
  }, 1500);
}

function showExplanation(id) {
  const note = notesData.find(n => n.id === id);
  const container = document.getElementById('ai-container');
  container.innerHTML = `<div class="ai-panel"><div class="ai-panel-header"><div class="ai-icon">💡</div><div class="ai-panel-title">AI Explanation</div></div><div class="ai-panel-body"><div class="ai-typing"><span></span><span></span><span></span></div></div></div>`;
  setTimeout(() => {
    container.querySelector('.ai-panel-body').innerHTML = `<p>${note.explanation}</p>`;
  }, 1800);
}

// ===== QUIZ =====
function openQuiz(subject) {
  const qs = quizzes[subject] || quizzes['Mathematics'];
  const qc = document.getElementById('quiz-content');
  qc.innerHTML = qs.map((q,i) => `
    <div class="quiz-question">
      <div class="quiz-q">${i+1}. ${q.q}</div>
      <div class="quiz-options">
        ${q.opts.map((o,j) => `<div class="quiz-option" onclick="selectOption(this,${j},${q.ans})">${o}</div>`).join('')}
      </div>
    </div>
  `).join('');
  document.getElementById('quiz-modal').classList.add('active');
}
function closeQuizModal() { document.getElementById('quiz-modal').classList.remove('active'); }
function selectOption(el, selected, correct) {
  const parent = el.parentElement;
  if (parent.querySelector('.selected')) return;
  const opts = parent.querySelectorAll('.quiz-option');
  opts[correct].classList.add('selected');
  if (selected !== correct) el.style.borderColor = 'var(--accent-rose)';
}

// ===== ADD/EDIT NOTES (Teacher Only) =====
function openAddModal() {
  document.getElementById('edit-note-id').value = '';
  document.getElementById('note-title-input').value = '';
  document.getElementById('note-subject-input').value = '';
  document.getElementById('note-content-input').value = '';
  document.getElementById('modal-title').textContent = 'Upload New Note';
  document.getElementById('submit-btn-text').textContent = 'Upload Note';
  document.getElementById('add-modal').classList.add('active');
}
function closeAddModal() { document.getElementById('add-modal').classList.remove('active'); }

function editNote(id) {
  const note = notesData.find(n => n.id === id);
  if (!note) return;
  document.getElementById('edit-note-id').value = id;
  document.getElementById('note-title-input').value = note.title;
  document.getElementById('note-subject-input').value = note.subject;
  document.getElementById('note-content-input').value = note.preview;
  document.getElementById('modal-title').textContent = 'Edit Note';
  document.getElementById('submit-btn-text').textContent = 'Save Changes';
  document.getElementById('add-modal').classList.add('active');
}

function handleSubmitNote(e) {
  e.preventDefault();
  const editId = document.getElementById('edit-note-id').value;
  const title = document.getElementById('note-title-input').value;
  const subject = document.getElementById('note-subject-input').value;
  const raw = document.getElementById('note-content-input').value;
  const fileInput = document.getElementById('note-file-input');
  const contentHTML = raw.split('\n').map(p => p.trim() ? `<p>${p}</p>` : '').join('');

  let fileData = null;
  if (fileInput.files && fileInput.files[0]) {
    const file = fileInput.files[0];
    fileData = {
      name: file.name,
      type: file.type,
      url: URL.createObjectURL(file)
    };
  }

  if (editId) {
    const note = notesData.find(n => n.id === parseInt(editId));
    if (note) {
      note.title = title;
      note.subject = subject;
      note.preview = raw.substring(0,150);
      note.content = contentHTML;
      if (fileData) note.file = fileData;
      showToast('Note updated successfully ✅');
    }
  } else {
    const newNote = {
      id: Date.now(),
      title,
      subject,
      author: 'You (Teacher)',
      date: new Date().toISOString().split('T')[0],
      preview: raw.substring(0,150),
      content: contentHTML,
      summary: 'AI summary will be generated for this note.',
      explanation: 'AI explanation will be generated for this note.',
      file: fileData
    };
    notesData.unshift(newNote);
    showToast('Note uploaded successfully 🎉');
  }
  closeAddModal();
  renderNotes();
}

function deleteNote(id) {
  if (!confirm('Are you sure you want to delete this note?')) return;
  const index = notesData.findIndex(n => n.id === id);
  if (index === -1) return;

  lastDeletedNote = { note: notesData[index], index };
  notesData = notesData.filter(n => n.id !== id);
  showToast('Note deleted 🗑️', 'Undo', undoDelete);
  renderNotes();
}

function undoDelete() {
  if (!lastDeletedNote) return;
  const { note, index } = lastDeletedNote;
  const insertIndex = Math.min(Math.max(index, 0), notesData.length);
  notesData.splice(insertIndex, 0, note);
  lastDeletedNote = null;
  showToast('Undo successful ✅');
  renderNotes();
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => { renderNotes(); });
