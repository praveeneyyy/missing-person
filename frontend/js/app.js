// Main Application Controller
const App = {
  activeTab: 'public-home',
  currentCaseId: null,
  activeCandidateId: null,

  init() {
    this.bindEvents();
    this.checkSession();
    this.renderCurrentView();

    // Default to investigator login for quick demo access
    if (!API.getToken()) {
      API.login('investigator', 'investigator123').catch(() => {});
    }
  },

  bindEvents() {
    // Navigation items
    document.querySelectorAll('[data-tab]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.getAttribute('data-tab');
        this.switchTab(tab);
      });
    });

    // Quick role switcher
    const roleSelect = document.getElementById('quick-role-select');
    if (roleSelect) {
      roleSelect.addEventListener('change', async (e) => {
        const val = e.target.value;
        if (val === 'investigator') {
          await API.login('investigator', 'investigator123');
          this.switchTab('dashboard');
        } else if (val === 'admin') {
          await API.login('admin', 'admin123');
          this.switchTab('dashboard');
        } else if (val === 'public') {
          API.logout();
          this.switchTab('public-home');
        }
      });
    }

    // Public sighting form
    const sightingForm = document.getElementById('sighting-form');
    if (sightingForm) {
      sightingForm.addEventListener('submit', (e) => this.handleSightingSubmit(e));
    }

    // Photo input live preview
    const sightingFile = document.getElementById('sighting-file');
    if (sightingFile) {
      sightingFile.addEventListener('change', (e) => this.handlePhotoPreview(e, 'sighting-preview-img', 'sighting-preview-box'));
    }

    // Case registration form
    const caseForm = document.getElementById('create-case-form');
    if (caseForm) {
      caseForm.addEventListener('submit', (e) => this.handleCaseSubmit(e));
    }

    const refFile = document.getElementById('case-photo-file');
    if (refFile) {
      refFile.addEventListener('change', (e) => this.handlePhotoPreview(e, 'case-preview-img', 'case-preview-box'));
    }

    // Sighting receipt lookup form
    const lookupForm = document.getElementById('receipt-lookup-form');
    if (lookupForm) {
      lookupForm.addEventListener('submit', (e) => this.handleReceiptLookup(e));
    }

    // Review submission form
    const reviewForm = document.getElementById('review-form');
    if (reviewForm) {
      reviewForm.addEventListener('submit', (e) => this.handleReviewSubmit(e));
    }

    // Listen for auth state changes
    window.addEventListener('auth-changed', () => {
      this.checkSession();
      this.renderCurrentView();
    });
  },

  checkSession() {
    const user = API.getUser();
    const userBadge = document.getElementById('user-profile-badge');
    const roleSelect = document.getElementById('quick-role-select');
    const staffNav = document.getElementById('staff-navigation');

    if (user) {
      if (userBadge) {
        userBadge.innerHTML = `
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span class="font-medium text-slate-800">${user.full_name}</span>
            <span class="text-xs bg-blue-100 text-blue-800 font-semibold px-2 py-0.5 rounded">${user.role.toUpperCase()}</span>
          </div>
        `;
      }
      if (roleSelect) {
        roleSelect.value = user.role;
      }
      if (staffNav) {
        staffNav.classList.remove('hidden');
      }
    } else {
      if (userBadge) {
        userBadge.innerHTML = `
          <span class="text-xs bg-slate-100 text-slate-600 font-medium px-2 py-1 rounded">Public Visitor</span>
        `;
      }
      if (roleSelect) {
        roleSelect.value = 'public';
      }
      if (staffNav) {
        staffNav.classList.add('hidden');
      }
    }
  },

  switchTab(tabName) {
    this.activeTab = tabName;

    // Update active button classes
    document.querySelectorAll('[data-tab]').forEach(btn => {
      if (btn.getAttribute('data-tab') === tabName) {
        btn.classList.add('bg-blue-50', 'text-blue-700', 'font-semibold');
        btn.classList.remove('text-slate-600');
      } else {
        btn.classList.remove('bg-blue-50', 'text-blue-700', 'font-semibold');
        btn.classList.add('text-slate-600');
      }
    });

    // Hide all tab panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
      pane.classList.add('hidden');
    });

    // Show target tab pane
    const target = document.getElementById(`tab-${tabName}`);
    if (target) {
      target.classList.remove('hidden');
    }

    this.renderCurrentView();
  },

  async renderCurrentView() {
    switch (this.activeTab) {
      case 'dashboard':
        await this.loadDashboard();
        break;
      case 'cases':
        await this.loadCases();
        break;
      case 'review-queue':
        await this.loadReviewQueue();
        break;
      case 'map':
        setTimeout(() => MapManager.initMainMap('investigation-map'), 100);
        break;
      case 'audit':
        await this.loadAuditLogs();
        break;
      case 'benchmark':
        await this.loadBenchmark();
        break;
      case 'public-submit':
        setTimeout(() => MapManager.initLocationPicker('sighting-picker-map', 'sighting-lat', 'sighting-lng', 'sighting-location'), 100);
        break;
    }
  },

  // 1. Dashboard View
  async loadDashboard() {
    try {
      const stats = await API.getDashboardStats();
      document.getElementById('stat-open-cases').innerText = stats.open_cases;
      document.getElementById('stat-pending-reviews').innerText = stats.pending_reviews;
      document.getElementById('stat-verified-matches').innerText = stats.verified_matches;
      document.getElementById('stat-total-sightings').innerText = stats.total_sightings;

      // Load recent cases table
      const cases = await API.getCases();
      const casesTbody = document.getElementById('dashboard-recent-cases');
      if (casesTbody) {
        casesTbody.innerHTML = cases.slice(0, 5).map(c => `
          <tr class="border-b border-slate-100 hover:bg-slate-50">
            <td class="py-3 px-4 font-mono font-medium text-blue-700">${c.reference_no}</td>
            <td class="py-3 px-4 font-semibold text-slate-800">${c.full_name}</td>
            <td class="py-3 px-4 text-sm text-slate-600">${c.last_seen_date}</td>
            <td class="py-3 px-4 text-sm text-slate-600">${c.last_seen_location}</td>
            <td class="py-3 px-4"><span class="badge badge-${c.status}">${c.status}</span></td>
            <td class="py-3 px-4">
              <button onclick="App.viewCaseDetails(${c.id})" class="text-xs bg-slate-100 hover:bg-blue-600 hover:text-white px-3 py-1 rounded transition">View Case</button>
            </td>
          </tr>
        `).join('');
      }

      // Load recent sightings
      const sightings = await API.getSightings();
      const sightingsTbody = document.getElementById('dashboard-recent-sightings');
      if (sightingsTbody) {
        sightingsTbody.innerHTML = sightings.slice(0, 5).map(s => `
          <tr class="border-b border-slate-100 hover:bg-slate-50">
            <td class="py-3 px-4 font-mono font-medium text-amber-700">${s.receipt_no}</td>
            <td class="py-3 px-4 text-sm text-slate-800">${s.location_name}</td>
            <td class="py-3 px-4 text-sm text-slate-600">${s.sighting_date}</td>
            <td class="py-3 px-4 text-sm font-semibold ${s.top_similarity >= 0.7 ? 'text-emerald-700' : 'text-slate-600'}">
              ${s.top_similarity ? (s.top_similarity * 100).toFixed(1) + '%' : 'Processing'}
            </td>
            <td class="py-3 px-4"><span class="badge badge-${s.status}">${s.status}</span></td>
            <td class="py-3 px-4">
              <button onclick="App.switchTab('review-queue')" class="text-xs bg-blue-50 text-blue-700 hover:bg-blue-600 hover:text-white px-3 py-1 rounded transition">Review</button>
            </td>
          </tr>
        `).join('');
      }
    } catch (err) {
      console.error('Error loading dashboard:', err);
    }
  },

  // 2. Cases Management
  async loadCases() {
    try {
      const search = document.getElementById('cases-search')?.value || '';
      const statusFilter = document.getElementById('cases-status-filter')?.value || '';
      const cases = await API.getCases(statusFilter, search);
      const container = document.getElementById('cases-grid');

      if (!container) return;

      if (cases.length === 0) {
        container.innerHTML = `
          <div class="col-span-full p-8 text-center bg-white rounded-xl border border-slate-200">
            <p class="text-slate-500">No missing-person cases match your query.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = cases.map(c => `
        <div class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition">
          <div class="h-44 bg-slate-100 relative overflow-hidden">
            ${c.primary_photo_path
              ? `<img src="/${c.primary_photo_path}" class="w-full h-full object-cover" alt="${c.full_name}"/>`
              : `<div class="w-full h-full flex items-center justify-center text-slate-400">No Photo Enrolled</div>`}
            <div class="absolute top-3 left-3">
              <span class="bg-white/90 backdrop-blur font-mono font-bold text-xs px-2.5 py-1 rounded shadow-sm text-slate-800">${c.reference_no}</span>
            </div>
            <div class="absolute top-3 right-3">
              <span class="badge badge-${c.status}">${c.status}</span>
            </div>
          </div>
          <div class="p-5">
            <h3 class="text-lg font-bold text-slate-900">${c.full_name}</h3>
            <p class="text-xs text-slate-500 mt-0.5">${c.age || 'Unknown'} yrs • ${c.gender || 'Not specified'}</p>
            <div class="mt-3 text-xs text-slate-600 space-y-1">
              <div><span class="font-semibold text-slate-700">Last Seen:</span> ${c.last_seen_date} ${c.last_seen_time || ''}</div>
              <div class="truncate"><span class="font-semibold text-slate-700">Location:</span> ${c.last_seen_location}</div>
              <div><span class="font-semibold text-slate-700">Investigator:</span> ${c.investigator_name || 'Assigned'}</div>
            </div>
            <div class="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
              <span class="text-xs text-slate-500">${c.reference_photo_count} Reference Photo(s)</span>
              <button onclick="App.viewCaseDetails(${c.id})" class="text-xs bg-blue-600 hover:bg-blue-700 text-white font-medium px-3.5 py-1.5 rounded-lg transition">Case Details</button>
            </div>
          </div>
        </div>
      `).join('');
    } catch (err) {
      console.error('Error loading cases:', err);
    }
  },

  async viewCaseDetails(caseId) {
    this.currentCaseId = caseId;
    try {
      const c = await API.getCase(caseId);
      this.switchTab('case-detail');

      document.getElementById('case-detail-ref').innerText = c.reference_no;
      document.getElementById('case-detail-name').innerText = c.full_name;
      document.getElementById('case-detail-status').innerText = c.status;
      document.getElementById('case-detail-status').className = `badge badge-${c.status}`;
      document.getElementById('case-detail-age').innerText = `${c.age || 'N/A'} yrs`;
      document.getElementById('case-detail-gender').innerText = c.gender || 'N/A';
      document.getElementById('case-detail-lastseen').innerText = `${c.last_seen_date} ${c.last_seen_time || ''}`;
      document.getElementById('case-detail-location').innerText = c.last_seen_location;
      document.getElementById('case-detail-features').innerText = c.identifying_features || 'None specified';
      document.getElementById('case-detail-clothing').innerText = c.clothing_description || 'None specified';
      document.getElementById('case-detail-notes').innerText = c.notes || 'No confidential case notes recorded.';

      // Reference photos
      const photoContainer = document.getElementById('case-detail-photos');
      if (photoContainer) {
        if (c.reference_photos.length === 0) {
          photoContainer.innerHTML = `<p class="text-slate-400 text-sm">No photos enrolled yet.</p>`;
        } else {
          photoContainer.innerHTML = c.reference_photos.map(p => `
            <div class="relative rounded-lg border border-slate-200 overflow-hidden bg-slate-50">
              <img src="/${p.file_path}" class="w-full h-48 object-cover" alt="Reference Photo"/>
              <div class="p-2.5 text-xs bg-white border-t border-slate-100">
                <div class="font-medium text-slate-800">128-D Vector Enrolled</div>
                <div class="text-slate-500 mt-0.5">${p.model_name} • ${p.model_version}</div>
              </div>
            </div>
          `).join('');
        }
      }

      // Linked leads
      const leadsContainer = document.getElementById('case-detail-leads');
      if (leadsContainer) {
        if (c.linked_leads.length === 0) {
          leadsContainer.innerHTML = `<p class="text-slate-500 text-sm py-4">No sighting leads have matched this case yet.</p>`;
        } else {
          leadsContainer.innerHTML = c.linked_leads.map(lead => `
            <div class="p-4 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
              <div class="flex items-center gap-3">
                ${lead.sighting_photo_path ? `<img src="/${lead.sighting_photo_path}" class="w-12 h-12 rounded object-cover" alt="Sighting"/>` : ''}
                <div>
                  <div class="font-mono text-xs font-bold text-amber-800">${lead.receipt_no}</div>
                  <div class="text-xs text-slate-600 mt-0.5">${lead.location_name} • ${lead.sighting_date}</div>
                </div>
              </div>
              <div class="text-right">
                <div class="text-sm font-bold text-blue-700">${(lead.similarity_score * 100).toFixed(1)}% Match</div>
                <span class="badge badge-${lead.match_status}">${lead.match_status}</span>
              </div>
            </div>
          `).join('');
        }
      }
    } catch (err) {
      alert('Failed to load case details: ' + err.message);
    }
  },

  // 3. Candidate Review Queue (The Core Module!)
  async loadReviewQueue() {
    try {
      const candidates = await API.getPendingCandidates();
      const container = document.getElementById('review-queue-list');
      if (!container) return;

      if (candidates.length === 0) {
        container.innerHTML = `
          <div class="p-12 text-center bg-white rounded-xl border border-slate-200">
            <div class="w-12 h-12 mx-auto rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold text-xl mb-3">✓</div>
            <h3 class="text-lg font-bold text-slate-800">Review Queue Clear</h3>
            <p class="text-slate-500 text-sm mt-1">All potential sighting matches have been reviewed by investigators.</p>
          </div>
        `;
        return;
      }

      container.innerHTML = candidates.map(c => {
        const scorePercent = (c.similarity_score * 100).toFixed(1);
        const isHigh = c.similarity_score >= 0.70;
        const scoreColor = isHigh ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-amber-700 bg-amber-50 border-amber-200';

        return `
          <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-6">
            <!-- Header bar with mandatory disclaimer -->
            <div class="bg-slate-900 text-white px-6 py-3.5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <span class="font-mono font-bold text-amber-400">LEAD #${c.candidate_id}</span>
                <span class="mx-2 text-slate-500">•</span>
                <span class="text-xs text-slate-300">Sighting: ${c.receipt_no}</span>
                <span class="mx-2 text-slate-500">•</span>
                <span class="text-xs text-slate-300">Candidate Case: ${c.reference_no} (${c.person_name})</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold px-2.5 py-1 rounded border ${scoreColor}">
                  Score: ${scorePercent}% (${isHigh ? 'High Confidence' : 'Moderate'})
                </span>
                <span class="badge badge-pending">Requires Investigator Review</span>
              </div>
            </div>

            <!-- Mandatory Legal Notice Banner -->
            <div class="bg-amber-50 border-b border-amber-200 px-6 py-2.5 text-xs text-amber-800 flex items-center gap-2">
              <span class="font-bold">⚠️ INVESTIGATION NOTICE:</span>
              <span>AI similarity scores are mathematical ranking signals, not conclusive proof of identity. Autonomous confirmation is prohibited.</span>
            </div>

            <!-- Side-by-side Evidence Inspection Grid -->
            <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-50/50">
              <!-- Left: Sighting Evidence -->
              <div class="bg-white p-4 rounded-xl border border-slate-200">
                <div class="flex items-center justify-between mb-3">
                  <h4 class="font-bold text-slate-800 text-sm">Submitted Sighting Evidence</h4>
                  <span class="text-xs text-slate-500 font-mono">${c.receipt_no}</span>
                </div>
                <div class="h-64 rounded-lg overflow-hidden bg-slate-900 relative">
                  ${c.sighting_photo_path ? `<img src="/${c.sighting_photo_path}" class="w-full h-full object-contain" alt="Sighting Photo"/>` : ''}
                  <div class="absolute bottom-2 left-2 bg-black/75 text-white text-xs px-2 py-1 rounded">
                    Detected Face #${c.sighting_face_index + 1}
                  </div>
                </div>
                <div class="mt-3 text-xs text-slate-600 space-y-1">
                  <div><span class="font-semibold text-slate-700">Location:</span> ${c.location_name}</div>
                  <div><span class="font-semibold text-slate-700">Reported Date/Time:</span> ${c.sighting_date} ${c.sighting_time || ''}</div>
                  <div><span class="font-semibold text-slate-700">Reporter Description:</span> "${c.sighting_notes || 'No description provided'}"</div>
                </div>
              </div>

              <!-- Right: Enrolled Reference Photo -->
              <div class="bg-white p-4 rounded-xl border border-slate-200">
                <div class="flex items-center justify-between mb-3">
                  <h4 class="font-bold text-slate-800 text-sm">Registered Missing Person Record</h4>
                  <span class="text-xs font-mono font-bold text-blue-700">${c.reference_no}</span>
                </div>
                <div class="h-64 rounded-lg overflow-hidden bg-slate-900 relative">
                  ${c.reference_photo_path ? `<img src="/${c.reference_photo_path}" class="w-full h-full object-contain" alt="Reference Photo"/>` : ''}
                  <div class="absolute bottom-2 left-2 bg-blue-900/90 text-white text-xs px-2 py-1 rounded">
                    Authorized Reference Photo
                  </div>
                </div>
                <div class="mt-3 text-xs text-slate-600 space-y-1">
                  <div><span class="font-semibold text-slate-700">Full Name:</span> ${c.person_name} (${c.age || 'N/A'} yrs, ${c.gender || 'N/A'})</div>
                  <div><span class="font-semibold text-slate-700">Last Seen:</span> ${c.last_seen_date} at ${c.last_seen_location}</div>
                  <div><span class="font-semibold text-slate-700">Embedding Engine:</span> ${c.model_version} (128-D Cosine Metric)</div>
                </div>
              </div>
            </div>

            <!-- Adjudication Action Panel -->
            <div class="p-6 bg-white border-t border-slate-200">
              <div class="flex flex-wrap items-center justify-between gap-4">
                <div class="text-xs text-slate-500">
                  Select a disposition and record mandatory written rationale to advance this case lead.
                </div>
                <div class="flex items-center gap-2">
                  <button onclick="App.openReviewModal(${c.candidate_id}, 'rejected')" class="px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition">
                    Reject Lead
                  </button>
                  <button onclick="App.openReviewModal(${c.candidate_id}, 'request_more_info')" class="px-3.5 py-2 text-xs font-semibold rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 transition">
                    Request Info
                  </button>
                  <button onclick="App.openReviewModal(${c.candidate_id}, 'escalated')" class="px-3.5 py-2 text-xs font-semibold rounded-lg bg-orange-50 hover:bg-orange-100 text-orange-800 transition">
                    Escalate to Field Team
                  </button>
                  <button onclick="App.openReviewModal(${c.candidate_id}, 'verified')" class="px-4 py-2 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition">
                    ✓ Confirm Verified Match
                  </button>
                </div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      console.error('Error loading review queue:', err);
    }
  },

  openReviewModal(candidateId, disposition) {
    this.activeCandidateId = candidateId;
    const modal = document.getElementById('review-modal');
    const dispSelect = document.getElementById('review-disposition');
    if (dispSelect) dispSelect.value = disposition;
    if (modal) modal.classList.remove('hidden');
  },

  closeReviewModal() {
    const modal = document.getElementById('review-modal');
    if (modal) modal.classList.add('hidden');
    this.activeCandidateId = null;
  },

  async handleReviewSubmit(e) {
    e.preventDefault();
    if (!this.activeCandidateId) return;

    const disposition = document.getElementById('review-disposition').value;
    const rationale = document.getElementById('review-rationale').value.trim();
    const nextSteps = document.getElementById('review-next-steps')?.value.trim() || '';

    if (rationale.length < 5) {
      alert('Mandatory investigator rationale must be at least 5 characters.');
      return;
    }

    try {
      const res = await API.submitReview(this.activeCandidateId, disposition, rationale, nextSteps);
      alert(`Review recorded successfully! Disposition marked as '${disposition}'.`);
      this.closeReviewModal();
      document.getElementById('review-rationale').value = '';
      this.loadReviewQueue();
    } catch (err) {
      alert('Review submission failed: ' + err.message);
    }
  },

  // 4. Public Sighting Submission
  async handleSightingSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('sighting-submit-btn');
    if (btn) btn.disabled = true;

    try {
      const form = document.getElementById('sighting-form');
      const formData = new FormData(form);

      const res = await API.submitSighting(formData);

      // Show receipt modal
      document.getElementById('receipt-number-display').innerText = res.receipt_no;
      document.getElementById('receipt-faces-count').innerText = `${res.faces_detected_count} face(s) detected`;
      document.getElementById('receipt-location').innerText = res.location_name;
      document.getElementById('receipt-modal').classList.remove('hidden');

      form.reset();
      document.getElementById('sighting-preview-box').classList.add('hidden');
    } catch (err) {
      alert('Submission failed: ' + err.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  // 5. Case Registration
  async handleCaseSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('case-submit-btn');
    if (btn) btn.disabled = true;

    try {
      const fullName = document.getElementById('case-fullname').value.trim();
      const age = parseInt(document.getElementById('case-age').value) || null;
      const gender = document.getElementById('case-gender').value;
      const lastSeenDate = document.getElementById('case-date').value;
      const lastSeenTime = document.getElementById('case-time').value;
      const lastSeenLocation = document.getElementById('case-location').value;
      const lat = parseFloat(document.getElementById('case-lat').value) || 13.0827;
      const lng = parseFloat(document.getElementById('case-lng').value) || 80.2707;
      const features = document.getElementById('case-features').value;
      const clothing = document.getElementById('case-clothing').value;
      const notes = document.getElementById('case-notes').value;

      const photoInput = document.getElementById('case-photo-file');
      if (!photoInput.files || photoInput.files.length === 0) {
        alert('An authorized reference photo is required to enroll a missing-person case.');
        if (btn) btn.disabled = false;
        return;
      }

      // Step 1: Create Case
      const caseData = {
        full_name: fullName,
        age: age,
        gender: gender,
        last_seen_date: lastSeenDate,
        last_seen_time: lastSeenTime,
        last_seen_location: lastSeenLocation,
        latitude: lat,
        longitude: lng,
        identifying_features: features,
        clothing_description: clothing,
        notes: notes
      };

      const newCase = await API.createCase(caseData);

      // Step 2: Upload reference photo and run AI validation
      const refResult = await API.addReferencePhoto(newCase.id, photoInput.files[0]);

      alert(`Case ${newCase.reference_no} enrolled successfully with 128-D facial embeddings!`);
      this.closeModal('create-case-modal');
      document.getElementById('create-case-form').reset();
      this.switchTab('cases');
    } catch (err) {
      alert('Case registration error: ' + err.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  // 6. Public Receipt Lookup
  async handleReceiptLookup(e) {
    e.preventDefault();
    const receiptNo = document.getElementById('lookup-receipt-input').value.trim();
    if (!receiptNo) return;

    try {
      const res = await API.lookupReceipt(receiptNo);
      const container = document.getElementById('lookup-result-box');
      container.classList.remove('hidden');
      container.innerHTML = `
        <div class="p-5 bg-white border border-slate-200 rounded-xl space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-mono font-bold text-slate-800">${res.receipt_no}</span>
            <span class="badge badge-pending">${res.status}</span>
          </div>
          <p class="text-xs text-slate-600">Location: <span class="font-semibold">${res.location_name}</span></p>
          <p class="text-xs text-slate-600">Sighting Date: <span class="font-semibold">${res.sighting_date}</span></p>
          <p class="text-xs text-slate-500 pt-2 border-t border-slate-100">${res.notice}</p>
        </div>
      `;
    } catch (err) {
      alert(err.message);
    }
  },

  // 7. Audit Logs View
  async loadAuditLogs() {
    try {
      const logs = await API.getAuditLogs();
      const tbody = document.getElementById('audit-table-body');
      if (!tbody) return;

      tbody.innerHTML = logs.map(l => `
        <tr class="border-b border-slate-100 hover:bg-slate-50 font-mono text-xs">
          <td class="py-2.5 px-4 text-slate-500">${l.created_at}</td>
          <td class="py-2.5 px-4 font-semibold text-slate-800">${l.actor_name}</td>
          <td class="py-2.5 px-4 text-blue-700 font-bold">${l.action}</td>
          <td class="py-2.5 px-4 text-slate-600">${l.resource_type} #${l.resource_id}</td>
          <td class="py-2.5 px-4 text-slate-500 truncate max-w-xs">${JSON.stringify(l.details)}</td>
        </tr>
      `).join('');
    } catch (err) {
      console.error('Error loading audit logs:', err);
    }
  },

  // 8. AI Quality & Benchmark View
  async loadBenchmark() {
    try {
      const b = await API.getBenchmark();
      const container = document.getElementById('benchmark-metrics-box');
      if (!container) return;

      container.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div class="bg-white p-5 rounded-xl border border-slate-200">
            <div class="text-xs text-slate-500 font-medium">Recall@1 Accuracy</div>
            <div class="text-3xl font-extrabold text-emerald-600 mt-1">${b.metrics.recall_at_1_percent}%</div>
            <div class="text-xs text-slate-400 mt-1">Exact Top-1 enrolled match</div>
          </div>
          <div class="bg-white p-5 rounded-xl border border-slate-200">
            <div class="text-xs text-slate-500 font-medium">Recall@5 Accuracy</div>
            <div class="text-3xl font-extrabold text-blue-600 mt-1">${b.metrics.recall_at_5_percent}%</div>
            <div class="text-xs text-slate-400 mt-1">Target in Top-5 candidates</div>
          </div>
          <div class="bg-white p-5 rounded-xl border border-slate-200">
            <div class="text-xs text-slate-500 font-medium">High Threshold FMR (≥ 0.70)</div>
            <div class="text-3xl font-extrabold text-slate-800 mt-1">${b.metrics.false_match_rate_high_threshold_percent}%</div>
            <div class="text-xs text-slate-400 mt-1">Disjoint non-match false rate</div>
          </div>
        </div>

        <div class="bg-white p-6 rounded-xl border border-slate-200 space-y-4">
          <h4 class="font-bold text-slate-800 text-sm">Calibrated Operating Points (Cosine Thresholds)</h4>
          <div class="space-y-3">
            ${b.operating_points.map(op => `
              <div class="p-3.5 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                <div>
                  <div class="font-bold text-sm text-slate-900">${op.label}</div>
                  <div class="text-xs text-slate-600 mt-0.5">${op.action}</div>
                </div>
                <span class="text-xs font-mono font-semibold text-slate-700 bg-white px-2.5 py-1 rounded border border-slate-200">
                  FMR Risk: ${op.false_match_risk}
                </span>
              </div>
            `).join('')}
          </div>
        </div>

        <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-900 flex items-start gap-2.5">
          <span class="text-base">ℹ️</span>
          <div>
            <span class="font-bold">Evaluation Governance Note:</span>
            <span>${b.governance_note} Processing latency: ${b.latency_profile.all_pairs_search_time_ms} ms per batch. Model architecture: ${b.model_architecture} (128-D).</span>
          </div>
        </div>
      `;
    } catch (err) {
      console.error('Error loading benchmark:', err);
    }
  },

  handlePhotoPreview(event, imgId, boxId) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = document.getElementById(imgId);
        const box = document.getElementById(boxId);
        if (img) img.src = e.target.result;
        if (box) box.classList.remove('hidden');
      };
      reader.readAsDataURL(file);
    }
  },

  openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
  },

  closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  }
};

window.App = App;
document.addEventListener('DOMContentLoaded', () => App.init());
