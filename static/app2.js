
import { h, ui } from './nurulib/util.js'
import { Network } from './nurulib/network.js'
import { Css } from './widgets.js'
import { Kinect } from './kinect.js'
import { NcaView } from './nca.js'


fetch('/defs').then(resp => resp.json()).then(defs => {
  const network = Network(null, {secondary: true})
  const sz = 0.43 * Math.min(window.innerWidth, window.innerHeight)
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
  NcaView('#bottom', { network, height: 0.7 * sz })
})

document.addEventListener('gesturestart', function (e) {
  e.preventDefault();
});
