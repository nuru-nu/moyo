
import { h, ui } from './smanmi/util.js'
import { Network } from './smanmi/network.js'

const Settings = (output, { network }) => {
  function slider(name) {
    return h.div().of(
      h.span().of(name),
      ui.range(name, {network}),
    )
  }
  const els = h.div().of(
    ui.h(
      h.button('next').of('▶▶'),
      ' nca=',
      h.span('nca').of('?'),
      ' ',
      h.a('img', {href: '#', target: '_blank'}).of('img'),
    ),
    h.div().of(
      h.button('sparkle').of('sparkle'),
      slider('speed'),
      slider('hue'),
      slider('saturation'),
      slider('value'),
      // slider('head'),
    ),
  ).into(output).els

  let nca = null
  network.listenJson('signals', data => {
    if (data.nca && data.nca != nca) {
      els.nca.textContent = data.nca
      const [group, num] = data.nca.split('_')
      els.img.href = `https://www.robots.ox.ac.uk/~vgg/data/dtd/thumbs/${group}/${data.nca}.jpg`
      nca = data.nca
    }
  })
}

const network = Network(null, {secondary: true})
Settings('#settings', {network})
