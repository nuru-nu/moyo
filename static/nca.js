import { h, u, ui } from './smanmi/util.js'

export const NCA = (output, {network, defs}) => {
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
        if (key === 'nca' || key[0] == '_') continue
        network.sender({[`nca_${key}`]: value})
      }
    })
  }

  const els = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('NCA'),
    h.div().of(
      h.div().of(
        ui.toggle('nca_clip', {network, text: 'clip'}), ' ',
        ui.toggle('nca_wrap', {network, text: 'wrap'}), ' ',
        h.a('nca', {href: '#', target: '_blank'}).of('?'), ' ',
        h.a('img', {href: '#', target: '_blank'}).of('img'), ' ',
      ),
      ui.range('nca_speed', {
        network, min: 0.01, max: 10,
        // trafo: [x =>x**5, x=>x**(1/5)],
        // trafo: [x => Math.exp(x) - 1e-6, x => Math.log(x + 1e-6)],
      }),
      h.div('buttons', {style: 'flex-wrap:wrap'}).of(
        h.button('next').of('ᐅ'),
      ),
    ),
  ).into(output).els

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