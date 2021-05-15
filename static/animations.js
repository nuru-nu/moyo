import { h, u, ui } from './smanmi/util.js'
import { ActionsButtons, Header } from './widgets.js'

export const Animations = (output, {network, defs}) => {
  const ncanames = {}
  const ncabuttons = {}
  const presets = defs.nca.presets

  function addbutton(name) {
    let nca = presets[name]
    if ('object' !== typeof nca) nca = {nca}
    ncabuttons[name] = h.button().of(name).into(els.buttons).el
    if (ncanames.hasOwnProperty(nca.nca)) {
      console.warn('Using', nca.nca, 'multiple times:', ncanames[nca.nca], name)
    }
    ncanames[nca.nca] = name
    ncabuttons[name].addEventListener('click', () => {
      network.sender({nca: nca.nca})
      for (const [key, value] of Object.entries(nca)) {
        if (key === 'info') continue
        network.sender({[key]: value})
      }
    })
  }

  const els = Header('anim', h.div().of(
    ActionsButtons(output, { name: 'animation', values: defs.animations, network }),
    ui.h(
      ui.range('anim_both', { network, name: 'both', text: 'both' }),
      ui.range('anim_head', { network, name: 'head', text: 'head' }),
      ui.range('anim_arms', { network, name: 'arms', text: 'arms' }),
    ),
    ui.h(
      ui.range('anim_hue', { network, name: 'arms', text: 'hue' }),
      ui.range('anim_sat', { network, name: 'arms', text: 'sat', max: 4 }),
    ),
    ui.h(
      ui.choice('anim_sig', { network, values: ['one', 'closest', 'rnd1', 'arousal'] }),
      '...',
      ui.toggle('anim_heart', { network, text: 'heart' }),
      ui.toggle('heart_sim', { network, text: 'sim' }),
      '...',
      ui.toggle('anim_into', { network, text: 'into' }),
    ),
    ui.h(
      h.button('next').of('ᐅ'), h.span('.s1'),
      ui.toggle('nca_clip', {network, text: 'clip'}), h.span('.s1'),
      ui.toggle('nca_wrap', {network, text: 'wrap'}), h.span('.s1'),
      h.a('nca', {href: '#', target: '_blank'}).of('?'), h.span('.s1'),
      h.a('img', {href: '#', target: '_blank'}).of('img'), h.span('.s1'),
      ui.range('nca_speed', {
        network, min: 0.01, max: 10, text: 'speed',
        // trafo: [x =>x**5, x=>x**(1/5)],
        // trafo: [x => Math.exp(x) - 1e-6, x => Math.log(x + 1e-6)],
      }),
    ),
    h.div('buttons', {style: 'flex-wrap:wrap'}).of(
    ),
  )).into(output).els

  Object.keys(defs.nca.presets).forEach(addbutton)

  els.next.addEventListener('click', () => {
    network.sender({ action: 'nca=next' })
  })

  let last_nca = null
  network.listenJson('signals', data => {
    if (data.nca && data.nca != last_nca) {
      let name
      if (last_nca) {
        name = ncanames[last_nca]
        if (name) {
          ncabuttons[name].classList.remove('on')
        }
      }
      last_nca = data.nca
      name = ncanames[last_nca]
      if (name) {
        ncabuttons[name].classList.add('on')
      }
      els.nca.textContent = data.nca
      els.nca.href = `/nca?name=${data.nca}`
      const [group, num] = data.nca.split('_')
      els.img.href = `https://www.robots.ox.ac.uk/~vgg/data/dtd/thumbs/${group}/${data.nca}.jpg`
    }
  })
};