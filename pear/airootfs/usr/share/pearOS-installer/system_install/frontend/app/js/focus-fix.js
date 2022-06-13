/**
  This file changes focus/blur behavior to macOS-like
  Focus is set by mouse click only on mouse focusable tags
  Clicking anywhere except these elements doesn't remove focus
 */

(function () {
  const mouseFocusableTags = [
    'option'
  ]

  const app = document.querySelector('.app');

  const handleClick = e => {
    const targetTag = e.target.tagName.toLowerCase();
    
    if (mouseFocusableTags.indexOf(targetTag)  !== -1) {
      return;
    }

    e.preventDefault();
  }

  app.addEventListener('mousedown', handleClick);
})()