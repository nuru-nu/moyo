
import { h, ui } from './smanmi/util.js'
import { Network } from './smanmi/network.js'
import { Css, ImageGPT } from './widgets.js'


fetch('/defs').then(resp => resp.json()).then(defs => {
  const network = Network(null, {secondary: true})
  const sz = 0.43 * Math.min(window.innerWidth, window.innerHeight)
  ImageGPT('#left', {
    network,
    headless: true,
  })
  Css('#right', {
    network,
    readonly: true,
    headless: true,
    hidestate: true,
    width: sz, height: sz,
  })
})

document.addEventListener('gesturestart', function (e) {
  e.preventDefault();
});
