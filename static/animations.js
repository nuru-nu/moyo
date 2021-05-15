import { h, u, ui } from './smanmi/util.js'
import { ActionsButtons, Header } from './widgets.js'

export const Animations = (output, {network, defs}) => {
  const presets = defs.presets

  function make_button(preset, idx) {
    preset.index = idx
    const button = h.button().of(preset.name).el
    button.addEventListener('click', () => {
      network.sender(preset.signals)
      const animation = preset.signals.animation || 'nca'
      network.sender({action: `animation=${animation}`})
      preset_active = preset_active === idx ? null : idx
      preset_buttons.forEach((b, i) =>
        b.classList[i === preset_active ? 'add' : 'remove']('on'))
      els.name.value = preset.name
      els.author.value = preset.author
    })
    return button
  }
  let preset_active = null
  const preset_buttons = presets.animations.map(make_button)

  const els = Header('anim', h.div().of(
    h.div().of('~~FUNCS~~'),
    ActionsButtons({ name: 'animation', values: defs.animations, network }),
    h.div({style: 'margin-top:1rem'}).of('~~SETTINGS~~'),
    ui.h(
      ui.range('anim_both', { network, text: 'both' }),
      ui.range('anim_head', { network, text: 'head' }),
      ui.range('anim_arms', { network, text: 'arms' }),
    ),
    ui.h(
      ui.range('anim_hue', { network, text: 'hue' }),
      ui.range('anim_sat', { network, text: 'sat', max: 4 }),
      h.button('reset').of('reset')
    ),
    ui.h(
      ui.dropdown('palette', {network, values: defs.palettes}),
      ui.dropdown('image', {network, values: defs.images}),
      ui.range('v0', { network, text: null }),
      ui.range('v1', { network, text: null }),
      ui.range('v2', { network, text: null }),
    ),
    ui.h(
      ui.toggle('anim_dark', { network, text: 'dark' }),
      '...',
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
      h.a('img_a', {href: '#', target: '_blank'}).of(
        h.img('img', {style: 'max-width:50px;height:auto'}),
      ), h.span('.s1'),
      ui.range('nca_speed', {
        network, min: 0.01, max: 10, text: 'speed',
        // trafo: [x =>x**5, x=>x**(1/5)],
        // trafo: [x => Math.exp(x) - 1e-6, x => Math.log(x + 1e-6)],
      }),
    ),
    h.div({style: 'margin-top: 1rem'}).of('~~PRESETS~~'),
    ui.h(
      'author:',
      h.input('author', {type: 'text'}), h.span('s1'),
      'name:',
      h.input('name', {type: 'text'}), h.span('s1'),
      h.button('update').of('update'),
    ),
    h.div('buttons .flex', {style: 'flex-wrap:wrap'}).of(
      preset_buttons,
      h.button('new').of('+'),
    ),
  )).into(output).els

  els.reset.addEventListener('click', () => network.sender({
    anim_hue: 0, anim_sat: 1, v0: .5, v1: .5, v2: .5,
  }))

  els.next.addEventListener('click', () => {
    const idx = Math.floor(presets.ncas.length * Math.random())
    network.sender({ nca: presets.ncas[idx] })
  })

  els.author.addEventListener('keyup', e => e.keyCode == 13 && els.update.click())
  els.name.addEventListener('keyup', e => e.keyCode == 13 && els.update.click())

  els.new.addEventListener('click', () => {
    const idx = presets.animations.length
    const preset = {
      name: `preset_#${idx}`,
      author: els.author.value,
      signals: { nca: last_nca },
    }
    presets.animations.push(preset)
    const button = make_button(preset, idx)
    preset_buttons.push(button)
    els.buttons.insertBefore(button, els.new)
    button.click()
  })

  els.update.addEventListener('click', () => {
    if (preset_active === null) return
    const preset = presets.animations[preset_active]
    preset.name = els.name.value
    preset.author = els.author.value
    preset.signals = last_signals
    network.sender({ preset })
    preset_buttons[preset_active].textContent = preset.name
  })

  let last_nca = null
  let last_signals = {}
  network.listenJson('signals', data => {
    if (data.nca && data.nca != last_nca) {
      preset_buttons.forEach((button, idx) => {
        const preset = presets.animations[idx]
        button.classList[
          preset.signals.nca === data.nca ? 'add' : 'remove']('active')
      })
      els.nca.textContent = data.nca
      els.nca.href = `/nca?name=${data.nca}`
      const [group, num] = data.nca.split('_')
      els.img_a.href = `https://www.robots.ox.ac.uk/~vgg/data/dtd/thumbs/${group}/${data.nca}.jpg`
      els.img.src = `https://www.robots.ox.ac.uk/~vgg/data/dtd/thumbs/${group}/${data.nca}.jpg`
      last_nca = data.nca
    }

    defs.monitor_def.preset_signals.forEach(name => {
      if (data.hasOwnProperty(name)) {
        last_signals[name] = data[name]
      }
    })
  })
};