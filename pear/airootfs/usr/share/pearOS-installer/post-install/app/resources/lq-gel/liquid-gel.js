class liquidGel {
  constructor() {
    this.config = {
      radius: 49,
      border: 0.09,
      lightness: 49,
      displace: 1.8, //output blur
      blend: "difference",
      x: "R",
      y: "B",
      alpha: 0.97,
      blur: 10,
      r: 0,
      g: 10,
      b: 20,
      saturation: 0.7,
      scale: -180,
      frost: 0.02,
    };
    this.elements = [];
    this.init();
  }

  init() {
    this.findElements();
    this.setupElements();
  }

  findElements() {
    this.elements = document.querySelectorAll('.liquid-gel');
    console.log(`Liquid Glass: Găsite ${this.elements.length} elemente`);
  }

  setupElements() {
    this.elements.forEach((element, index) => {
      this.createliquidGelEffect(element, index);
    });
  }

  createliquidGelEffect(element, index) {
    const effectDiv = document.createElement('div');
    effectDiv.className = 'effect';
    
    effectDiv.style.position = 'fixed';
    effectDiv.style.zIndex = '999999';
    effectDiv.style.opacity = '0';
    effectDiv.style.transition = 'opacity 0.26s ease-out';
    effectDiv.style.pointerEvents = 'none';
    
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'filter');
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const filter = document.createElementNS('http://www.w3.org/2000/svg', 'filter');
    filter.setAttribute('id', `filter-${index}`);
    filter.setAttribute('color-interpolation-filters', 'sRGB');
    
    const feImage = document.createElementNS('http://www.w3.org/2000/svg', 'feImage');
    feImage.setAttribute('x', '0');
    feImage.setAttribute('y', '0');
    feImage.setAttribute('width', '100%');
    feImage.setAttribute('height', '100%');
    feImage.setAttribute('result', 'map');
    
    const feDisplacementMapRed = document.createElementNS('http://www.w3.org/2000/svg', 'feDisplacementMap');
    feDisplacementMapRed.setAttribute('in', 'SourceGraphic');
    feDisplacementMapRed.setAttribute('in2', 'map');
    feDisplacementMapRed.setAttribute('id', `redchannel-${index}`);
    feDisplacementMapRed.setAttribute('xChannelSelector', this.config.x);
    feDisplacementMapRed.setAttribute('yChannelSelector', this.config.y);
    feDisplacementMapRed.setAttribute('result', 'dispRed');
    
    const feColorMatrixRed = document.createElementNS('http://www.w3.org/2000/svg', 'feColorMatrix');
    feColorMatrixRed.setAttribute('in', 'dispRed');
    feColorMatrixRed.setAttribute('type', 'matrix');
    feColorMatrixRed.setAttribute('values', '1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0');
    feColorMatrixRed.setAttribute('result', 'red');
    
    const feDisplacementMapGreen = document.createElementNS('http://www.w3.org/2000/svg', 'feDisplacementMap');
    feDisplacementMapGreen.setAttribute('in', 'SourceGraphic');
    feDisplacementMapGreen.setAttribute('in2', 'map');
    feDisplacementMapGreen.setAttribute('id', `greenchannel-${index}`);
    feDisplacementMapGreen.setAttribute('xChannelSelector', this.config.x);
    feDisplacementMapGreen.setAttribute('yChannelSelector', this.config.y);
    feDisplacementMapGreen.setAttribute('result', 'dispGreen');
    
    const feColorMatrixGreen = document.createElementNS('http://www.w3.org/2000/svg', 'feColorMatrix');
    feColorMatrixGreen.setAttribute('in', 'dispGreen');
    feColorMatrixGreen.setAttribute('type', 'matrix');
    feColorMatrixGreen.setAttribute('values', '0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 1 0');
    feColorMatrixGreen.setAttribute('result', 'green');
    
    const feDisplacementMapBlue = document.createElementNS('http://www.w3.org/2000/svg', 'feDisplacementMap');
    feDisplacementMapBlue.setAttribute('in', 'SourceGraphic');
    feDisplacementMapBlue.setAttribute('in2', 'map');
    feDisplacementMapBlue.setAttribute('id', `bluechannel-${index}`);
    feDisplacementMapBlue.setAttribute('xChannelSelector', this.config.x);
    feDisplacementMapBlue.setAttribute('yChannelSelector', this.config.y);
    feDisplacementMapBlue.setAttribute('result', 'dispBlue');
    
    const feColorMatrixBlue = document.createElementNS('http://www.w3.org/2000/svg', 'feColorMatrix');
    feColorMatrixBlue.setAttribute('in', 'dispBlue');
    feColorMatrixBlue.setAttribute('type', 'matrix');
    feColorMatrixBlue.setAttribute('values', '0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 1 0');
    feColorMatrixBlue.setAttribute('result', 'blue');
    
    const feBlendRG = document.createElementNS('http://www.w3.org/2000/svg', 'feBlend');
    feBlendRG.setAttribute('in', 'red');
    feBlendRG.setAttribute('in2', 'green');
    feBlendRG.setAttribute('mode', 'screen');
    feBlendRG.setAttribute('result', 'rg');
    
    const feBlendRGB = document.createElementNS('http://www.w3.org/2000/svg', 'feBlend');
    feBlendRGB.setAttribute('in', 'rg');
    feBlendRGB.setAttribute('in2', 'blue');
    feBlendRGB.setAttribute('mode', 'screen');
    feBlendRGB.setAttribute('result', 'output');
    
    const feGaussianBlur = document.createElementNS('http://www.w3.org/2000/svg', 'feGaussianBlur');
    feGaussianBlur.setAttribute('in', 'output');
    feGaussianBlur.setAttribute('stdDeviation', this.config.displace);
    
    filter.appendChild(feImage);
    filter.appendChild(feDisplacementMapRed);
    filter.appendChild(feColorMatrixRed);
    filter.appendChild(feDisplacementMapGreen);
    filter.appendChild(feColorMatrixGreen);
    filter.appendChild(feDisplacementMapBlue);
    filter.appendChild(feColorMatrixBlue);
    filter.appendChild(feBlendRG);
    filter.appendChild(feBlendRGB);
    filter.appendChild(feGaussianBlur);
    
    defs.appendChild(filter);
    svg.appendChild(defs);
    effectDiv.appendChild(svg);
    
    document.body.appendChild(effectDiv);
    
    this.createDisplacementImage(element, feImage, index);
    
    const rect = element.getBoundingClientRect();
    effectDiv.style.top = `${rect.top}px`;
    effectDiv.style.left = `${rect.left}px`;
    effectDiv.style.width = `${element.offsetWidth}px`;
    effectDiv.style.height = `${element.offsetHeight}px`;
    effectDiv.style.borderRadius = `${this.config.radius}px`;
    
    effectDiv.style.overflow = 'hidden';
    
    effectDiv.style.background = `hsla(0 0% 100% / ${this.config.frost})`;
    effectDiv.style.backdropFilter = `url(#filter-${index}) saturate(${this.config.saturation})`;
    effectDiv.style.webkitBackdropFilter = `url(#filter-${index}) saturate(${this.config.saturation})`;
    
    effectDiv.style.isolation = 'isolate';
    effectDiv.style.mixBlendMode = 'normal';
    
    effectDiv.style.pointerEvents = 'none';
    
    effectDiv.style.boxShadow = `
      0 0 2px 1px rgba(0,0,0,0.1) inset,
      0 0 10px 4px rgba(0,0,0,0.05) inset,
      0px 4px 16px rgba(17, 17, 26, 0.05),
      0px 8px 24px rgba(17, 17, 26, 0.05),
      0px 16px 56px rgba(17, 17, 26, 0.05),
      0px 4px 16px rgba(17, 17, 26, 0.05) inset,
      0px 8px 24px rgba(17, 17, 26, 0.05) inset,
      0px 16px 56px rgba(17, 17, 26, 0.05) inset
    `;
    
    effectDiv.style.opacity = '1';
    
    element._liquidGelEffect = effectDiv;
    element._liquidGelFilter = `filter-${index}`;
    element._feImage = feImage;
    
    feDisplacementMapRed.setAttribute('scale', this.config.scale + this.config.r);
    feDisplacementMapGreen.setAttribute('scale', this.config.scale + this.config.g);
    feDisplacementMapBlue.setAttribute('scale', this.config.scale + this.config.b);
  }

  createDisplacementImage(element, feImage, index) {
    const width = element.offsetWidth;
    const height = element.offsetHeight;
    const border = Math.min(width, height) * (this.config.border * 0.5);
    
    const svg = `
      <svg class="displacement-image" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="red-${index}" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%" stop-color="#0000"/>
            <stop offset="100%" stop-color="red"/>
          </linearGradient>
          <linearGradient id="blue-${index}" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#0000"/>
            <stop offset="100%" stop-color="blue"/>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="${width}" height="${height}" fill="black"/>
        
        <rect x="0" y="0" width="${width}" height="${height}" rx="${this.config.radius}" fill="url(#red-${index})" />
        
        <rect x="0" y="0" width="${width}" height="${height}" rx="${this.config.radius}" fill="url(#blue-${index})" style="mix-blend-mode: ${this.config.blend}" />
        
        <rect x="${border}" y="${border}" width="${width - border * 2}" height="${height - border * 2}" rx="${this.config.radius}" fill="hsl(0 0% ${this.config.lightness}% / ${this.config.alpha})" style="filter:blur(${this.config.blur}px)" />
      </svg>
    `;
    
    const dataUri = `data:image/svg+xml,${encodeURIComponent(svg)}`;
    feImage.setAttribute('href', dataUri);
  }

  updateConfig(newConfig) {
    Object.assign(this.config, newConfig);
    this.elements.forEach(element => {
      if (element._liquidGelEffect) {
        const effect = element._liquidGelEffect;
        const rect = element.getBoundingClientRect();
        effect.style.top = `${rect.top}px`;
        effect.style.left = `${rect.left}px`;
        effect.style.width = `${element.offsetWidth}px`;
        effect.style.height = `${element.offsetHeight}px`;
      }
    });
  }

  addElement(element) {
    if (element.classList.contains('liquid-gel')) {
      this.elements.push(element);
      this.setupElements();
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.liquidGel = new liquidGel();
});

export default liquidGel;