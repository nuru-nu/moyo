import { h, u, ui } from './smanmi/util.js'

export const NCA = (output, {network, defs}) => {
  const ncanames = {}
  const ncabuttons = {}

  function addbutton(name, value) {
    ncabuttons[name] = h.button().of(name).into(els.buttons).el
    ncanames[value] = name
    ncabuttons[name].addEventListener('click', () => {
      const value = defs.nca.ncas[name]
      network.sender({ action: `nca=set=${value}`})
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
      ui.range('nca_speed', {network, min: 0.01, max: 10, trafo: [Math.exp, Math.log]}),
      h.div('buttons', {style: 'flex-wrap:wrap'}).of(
        h.button('next').of('ᐅ'),
      ),
    ),
  ).into(output).els

  Object.keys(defs.nca.ncas).forEach(name => {
    addbutton(name, defs.nca.ncas[name])
  })

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