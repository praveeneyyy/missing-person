// Map utilities using Leaflet.js
const MapManager = {
  mainMap: null,
  pickerMap: null,
  pickerMarker: null,

  initMainMap(containerId = 'investigation-map') {
    const el = document.getElementById(containerId);
    if (!el) return;

    if (this.mainMap) {
      this.mainMap.remove();
      this.mainMap = null;
    }

    // Default center: Chennai, Tamil Nadu
    this.mainMap = L.map(containerId).setView([13.05, 80.22], 11);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18
    }).addTo(this.mainMap);

    this.loadMapPoints();
  },

  async loadMapPoints() {
    if (!this.mainMap) return;

    try {
      const data = await API.getMapPoints();
      const bounds = [];

      // Custom icon generators
      const createIcon = (color, text) => L.divIcon({
        className: 'custom-map-pin',
        html: `<div style="background-color: ${color}; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);">${text}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      // Plot registered cases
      data.cases.forEach(c => {
        if (c.latitude && c.longitude) {
          bounds.push([c.latitude, c.longitude]);
          const marker = L.marker([c.latitude, c.longitude], {
            icon: createIcon('#2563EB', 'MP')
          }).addTo(this.mainMap);

          const photoHtml = c.photo_path
            ? `<img src="/${c.photo_path}" style="width: 100%; height: 90px; object-fit: cover; border-radius: 4px; margin-bottom: 6px;" alt="${c.full_name}"/>`
            : '';

          marker.bindPopup(`
            <div style="font-size: 13px; max-width: 220px;">
              ${photoHtml}
              <div style="font-weight: 700; color: #1E40AF;">${c.reference_no}</div>
              <div style="font-weight: 600; font-size: 14px; margin-top: 2px;">${c.full_name}</div>
              <div style="color: #64748B; font-size: 12px; margin-top: 4px;">Last Seen: ${c.last_seen_date}</div>
              <div style="color: #475569; font-size: 12px; margin-top: 2px;">${c.last_seen_location}</div>
              <div style="margin-top: 6px;"><span class="badge badge-${c.status}">${c.status}</span></div>
            </div>
          `);
        }
      });

      // Plot reported sightings
      data.sightings.forEach(s => {
        if (s.latitude && s.longitude) {
          bounds.push([s.latitude, s.longitude]);
          const color = s.status === 'verified_match' ? '#15803D' : (s.status === 'escalated' ? '#B91C1C' : '#D97706');
          const marker = L.marker([s.latitude, s.longitude], {
            icon: createIcon(color, 'ST')
          }).addTo(this.mainMap);

          const simText = s.max_similarity ? `<div style="color: #15803D; font-weight: 600; font-size: 12px; margin-top: 4px;">Top Match: ${(s.max_similarity * 100).toFixed(1)}%</div>` : '';

          marker.bindPopup(`
            <div style="font-size: 13px; max-width: 220px;">
              <div style="font-weight: 700; color: #92400E;">${s.receipt_no}</div>
              <div style="font-weight: 600; margin-top: 2px;">Sighting Report</div>
              <div style="color: #64748B; font-size: 12px; margin-top: 4px;">Date: ${s.sighting_date}</div>
              <div style="color: #475569; font-size: 12px; margin-top: 2px;">${s.location_name}</div>
              ${simText}
              <div style="margin-top: 6px;"><span class="badge badge-${s.status}">${s.status}</span></div>
            </div>
          `);
        }
      });

      if (bounds.length > 0) {
        this.mainMap.fitBounds(bounds, { padding: [40, 40] });
      }
    } catch (err) {
      console.error('Failed to load map points:', err);
    }
  },

  initLocationPicker(containerId, latInputId, lngInputId, locationNameId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    if (this.pickerMap) {
      this.pickerMap.remove();
      this.pickerMap = null;
    }

    const defaultLat = 13.0827;
    const defaultLng = 80.2707;

    this.pickerMap = L.map(containerId).setView([defaultLat, defaultLng], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap'
    }).addTo(this.pickerMap);

    this.pickerMarker = L.marker([defaultLat, defaultLng], { draggable: true }).addTo(this.pickerMap);

    const updateInputs = (lat, lng) => {
      const latEl = document.getElementById(latInputId);
      const lngEl = document.getElementById(lngInputId);
      if (latEl) latEl.value = lat.toFixed(5);
      if (lngEl) lngEl.value = lng.toFixed(5);
    };

    updateInputs(defaultLat, defaultLng);

    this.pickerMap.on('click', (e) => {
      this.pickerMarker.setLatLng(e.latlng);
      updateInputs(e.latlng.lat, e.latlng.lng);
    });

    this.pickerMarker.on('dragend', (e) => {
      const pos = e.target.getLatLng();
      updateInputs(pos.lat, pos.lng);
    });
  }
};
