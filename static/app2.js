
import { h, ui } from './smanmi/util.js'
import { Network } from './smanmi/network.js'
import { Css } from './widgets.js'
import { Kinect } from './kinect.js'


fetch('/defs').then(resp => resp.json()).then(defs => {
  const network = Network(null, {secondary: true})
  const sz = 0.40 * Math.min(window.innerWidth, window.innerHeight)
  Kinect('#left', {
    network,
    readonly: true,
    headless: true,
    width: sz, height: sz,
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
