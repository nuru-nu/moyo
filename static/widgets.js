import { h, u, ui, observe } from './smanmi/util.js'

export const Header = (name, el) => {
  const ret = h.div({class: 'flex widget'}).of(
    h.div('header', {class: 'header', style: 'cursor:pointer'}).of(name),
    h.div('cont').of(el),
    h.div('placeholder', {class: 'h'}).of('...'),
  )
  const els = ret.els
  els.header.addEventListener('click', () => {
    els.cont.classList.toggle('h')
    els.placeholder.classList.toggle('h')
  })
  return ret
}

export const Sonar = (output, {network}) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('sonar'),
    h.button('override').of('override'),
    h.input('sonar', {type: 'range', min: 0, max: 100, value: 100}),
    h.button('pir').of('pir'),
    h.button('pir_on .h').of('ON'),
  ).into(output).els

  let override = false
  disp.sonar.style.display = 'none'
  disp.override.addEventListener('click', () => {
    override = !override
    update()
  })
  disp.sonar.addEventListener('input', update)

  let pir_override
  disp.pir.addEventListener('click', () => {
    network.sender({pir_override: pir_override === null ? 0 : null})
  })
  disp.pir_on.addEventListener('click', () => {
    network.sender({pir_override: 1 * !pir_override})
  })

  function update() {
    if (!override) {
      network.sender({sonar_override: null})
      return
    }
    network.sender({sonar_override: parseInt(disp.sonar.value) / 100})
  }
  network.listenJson('signals', function(data) {
    const sonar_override = data.hasOwnProperty('sonar_override') && data.sonar_override !== null
    if (sonar_override !== disp.override.classList.contains('on')) {
      disp.override.classList.toggle('on')
      disp.sonar.style.display = override ? 'block' : 'none'
    }
    disp.sonar.value = 100 * data.sonar
    if (pir_override !== data.pir_override) {
      pir_override = data.pir_override
      disp.pir.classList[pir_override === null ? 'remove' : 'add']('on')
      disp.pir_on.classList[pir_override !== null ? 'remove' : 'add']('h')
      disp.pir_on.classList[pir_override ? 'add' : 'remove']('on')
    }
  })
}

export const Debug = (output, { network, record_timestamps }) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('debug'),
    h.button('download').of('download traces')
  ).into(output).els
  disp.download.addEventListener('click', network.download_timestamps)
  disp.download.style.display = record_timestamps ? 'inline-block' : 'none'
}

export const Subsample = (output, {network}) => {
  const subsamples = [1, 2, 5, 10, 15, 20, 30]
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('subsample'),
    h.div({class: 'flex'}).of(
      h.button('full', {class: 'on'}).of('full on'),
      h.div('controls', {style: 'display: none'}).of(
        'recorder', h.select('recorder').of(subsamples.map(
          value => h.option({value}).of(`1/${value}`))),
        'animator', h.select('animator').of(subsamples.map(
          value => h.option({value}).of(`1/${value}`))),
      ),
    ),
  ).into(output).els
  disp.recorder.value = disp.animator.value = 10

  let full = true
  disp.full.addEventListener('click', () => {
    full = !full
    disp.full.classList.toggle('on')
    disp.controls.style.display = full ? 'none' : 'block'
    update()
  })
  function update() {
    const subsample = full ? 1 : parseInt(disp.recorder.value)
    network.sender({ action: `subsample=${subsample}` })
  }
  disp.recorder.addEventListener('change', update)
  disp.animator.addEventListener('change', update)
}

export const Cmd = (output, {network, defs}) => {
  const actions = [
    'fc=0', 'fc=1', 'fc=2', 'fc=3', 'next',
    'growl=angry', 'growl=happy', 'sub=on', 'sub=off',
    'dream',
  ]
  const els = Header('cmd', h.div().of(
    ActionsButtons({name: 'mode', values: defs.modes, network}),
    h.div().of(
      actions.map(a => h.button(a).of(a)),
    ),
    'raw: ', h.input('raw', {type: 'text'}),
  )).into(output).els

  actions.forEach(action => els[action].addEventListener('click', () => {
    network.sender({ action })
  }))

  const lastraws = []
  let lastrawi = 0
  els.raw.addEventListener('keyup', e => {
    if (e.keyCode === 38 && lastrawi > 0) { // keyup
      e.target.value = lastraws[--lastrawi]
    }
    if (e.keyCode === 40 && lastrawi < lastraws.length - 1) { // keydown
      e.target.value = lastraws[++lastrawi]
    }
    if (e.keyCode === 13) {
      const [name, ...value] = e.target.value.split('=')
      network.sender({[name]: value.join('=')})
      if (lastraws.indexOf(e.target.value) === -1) {
        lastraws.push(e.target.value)
      }
      e.target.value = ''
      lastrawi = lastraws.length
    }
  })
}

export const Midi = (output) => {
  const notes = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
  ]
  const note_re = /(\d+): ([A-G]#?)(-?\d+) (.*)/
  const range_re = /^\d+:\sX\d+=\d+$/
  const channels = new Map()
  const keys = new Map()
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('midi'),
    ui.v(
      ui.h(
        'channel ',
        ui.choice('channel', {values: ['1', '2', '3', '4', '5']}),
        'octave ',
        ui.choice('octave', {values: ['0', '1', '2', '3', '4', '5'], initial: '2'}),
      ),
      notes.map(note => h.button(note).of(note)),
      h.div('cont'),
      ui.h(
        ui.choice('xchoice', {values: ['-', 'X1', 'X2', 'X3']}),
        ui.range('xrange'),
      )
    ),
  ).into(output).els

  let channel, octave
  disp.channel.change(value => channel = value).init()
  disp.octave.change(value => octave = value).init()
  function updatex(v) {
    const value = Math.round(parseFloat(v * 127))
    if (disp.xchoice.value !== '-') {
      sender({midi: `${channel}: ${disp.xchoice.value}=${value}`})
    }
  }
  disp.xchoice.change(updatex)
  disp.xrange.change(updatex)

  notes.forEach(note => {
    disp[note].addEventListener('mousedown', function() {
      this.classList.add('on')
      sender({midi: `${channel}: ${note}${octave} on`})
    })
    disp[note].addEventListener('mouseup', function() {
      this.classList.remove('on')
      sender({midi: `${channel}: ${note}${octave} off`})
    })
  })

  function value(note) {
    const octave = parseInt(note.substr(note.length - 1))
    const idx = notes.indexOf(note.substr(0, note.length - 1))
    return octave * 12 + idx
  }
  function sort(cont) {
    const arr = Array.from(cont.children).map(child => [
      value(child.textContent), child])
    while (cont.firstChild) cont.removeChild(cont.firstChild)
    arr.sort()
    arr.forEach(idx_child => cont.appendChild(idx_child[1]))
  }

  function listener(signals) {
    if (!signals.midi) return
    if (range_re.exec(signals.midi)) return
    const m = note_re.exec(signals.midi)
    if (m === null) {
      console.warn('Could not parse signals.midi', signals.midi)
      return
    }
    let [_, channel, letter, octave, command] = m
    if (!channels.has(channel)) {
      channels.set(channel, ui.h(
        `${channel}:`,
        h.div('cont'),
      ).into(disp.cont).els.cont)
    }
    const key = `${channel}:${letter}${octave}`
    if (!keys.has(key)) {
      keys.set(
        key, h.span('.key').of(
          `${letter}${octave}`,
        ).into(channels.get(channel)).el)
      sort(channels.get(channel))
    }
    if (command === 'on') {
      keys.get(key).classList.add('on')
    } else if (command === 'off') {
      keys.get(key).classList.remove('on')
    }
  }

  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    listener,
    sendto,
  }
}

export const Css = (output, {network, readonly, headless, width, height, hidestate}) => {
  width = width || 300
  height = height || 300
  const xlim = [-1, 1]  // Note: assumed [-1, 1] by background() below ...
  const ylim = [-1, 1]  // Note: assumed [-1, 1] by background() below ...
  const r = width / 50
  const disp = h.div({class: 'flex widget'}).of(
    headless ? [] : h.div({class: 'header'}).of('css'),
    ui.v(
      readonly ? [] : h.div().of(
        h.button('clear').of('clear'),
        ' α=',
        h.input('alpha', {type: 'range', min: 5, max: 100, value: 10}),
      ),
      h.canvas('xy .css', {width, height}),
      h.div('state', {style: 'text-align:center'}),
    ),
  ).into(output).els
  const ctx = disp.xy.getContext('2d')

  if (!readonly) {
    disp.clear.addEventListener('click', () => network.sender({target_css: null}))
    disp.alpha.addEventListener('input', e => {
      network.sender({css_alpha: parseFloat(e.target.value)})
    })
    disp.xy.addEventListener('click', e => {
      network.sender({target_css: [fromx(e.offsetX), fromy(e.offsetY)]})
    })
  }

  const tox = x => width  * (x - xlim[0]) / (xlim[1] - xlim[0])
  const toy = y => height - height * (y - ylim[0]) / (ylim[1] - ylim[0])
  const fromx = x => xlim[0] + x / width * (xlim[1] - xlim[0])
  const fromy = y => ylim[0] + (height - y) / height * (ylim[1] - ylim[0])

  function background(css) {
    var font_height = Math.floor(height / 20) * 1
    var font = `${font_height}px Arial`
    var font_height2 = Math.floor(height / 20) * 0.8
    var font2 = `${font_height2}px Arial`

    ctx.lineWidth = 1
    ctx.strokeStyle = ctx.fillStyle = 'white'
    ctx.globalAlpha = 0.2
    if (css[0] < -0.25 && css[1] > 0){
      ctx.globalAlpha = 1
    }
    ctx.globalAlpha = 1
    
    // Assuming you have a canvas context 'ctx'
    var centerX = tox(0);
    var centerY = toy(0);
    var radius = (tox(1) - tox(0));
    
    // Use conic gradient if supported
    var conicGradient = ctx.createConicGradient(0, centerX, centerY);
    
    // Define the color stops for the conic gradient
    conicGradient.addColorStop(0, 'rgb(128, 128, 64)'); // yellow/purple
    conicGradient.addColorStop(1/8, 'rgb(255, 255, 0)'); // yellow
    conicGradient.addColorStop(3/8, 'rgb(0, 0, 255)'); // blue
    conicGradient.addColorStop(5/8, 'rgb(255, 0, 0)'); // red
    conicGradient.addColorStop(7/8, 'rgb(128, 0, 128)'); // purple
    conicGradient.addColorStop(1, 'rgb(128, 128, 64)'); // yellow/purple

    
    // Draw the circle with the conic gradient
    ctx.fillStyle = conicGradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.fill();
    
    // Create radial gradient for the alpha fade
    var radialGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
    radialGradient.addColorStop(0, 'rgba(100, 100, 100, 1)'); // Opaque in the center
    radialGradient.addColorStop(0.85, 'rgba(0, 0, 0, 0)');
    radialGradient.addColorStop(1, 'rgba(0, 0, 0, 1)'); // Transparent towards the edges
    
    // Overlay the radial gradient
    ctx.fillStyle = radialGradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.fill();
    
    ctx.globalAlpha = 1
    
    ctx.strokeStyle = ctx.fillStyle = 'white'
    ctx.font = font2
    ctx.beginPath()
    ctx.moveTo(0, height/2)
    ctx.lineTo(width, height/2)
    ctx.moveTo(width/2, 0)
    ctx.lineTo(width/2, height)
    ctx.closePath()

    // Arrow Heads
    const darr = height / 30
    var x =  width / 2 - ctx.measureText("High").width - font_height2 / 2
    ctx.fillText("High", x, 2* darr + font_height2 / 2);
    ctx.fillText("Arousal", width / 2 + font_height2 / 2, 2* darr + font_height2 / 2);
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(width/2, 0)
    ctx.lineTo(width/2-darr, darr)
    ctx.lineTo(width/2+darr, darr)
    ctx.closePath()
    ctx.fill()

    var x =  width / 2 - ctx.measureText("Low").width - font_height2 / 2
    ctx.fillText("Low", x, height - darr - font_height2 / 2);
    ctx.fillText("Arousal", width / 2 + font_height2 / 2, height - darr - font_height2 / 2);
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(width/2, height)
    ctx.lineTo(width/2-darr, height-darr)
    ctx.lineTo(width/2+darr, height-darr)
    ctx.closePath()
    ctx.fill()

    var x =  (width / 2 - ctx.measureText("Negative").width) / 5
    ctx.fillText("Negative", x, height / 2 + 3*font_height2 / 3);
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(0, height/2)
    ctx.lineTo(darr, height/2-darr)
    ctx.lineTo(darr, height/2+darr)
    ctx.closePath()
    ctx.fill()

    var x =  (width / 2 - ctx.measureText("Positive").width) / 2 + width / 1.6 
    ctx.fillText("Positive", x, height / 2 + 3*font_height2 / 3);
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(width, height/2)
    ctx.lineTo(width-darr, height/2-darr)
    ctx.lineTo(width-darr, height/2+darr)
    ctx.closePath()
    ctx.fill()

    ctx.stroke()

    ctx.font = font;
    ctx.fillStyle = 'white';
    
    // Define the radius for text placement
    var textRadius = radius * 0.6; // Adjust as needed for positioning outside the circle
    
    // Function to place text at a given angle around the circle
    function placeText(text, angle) {
        var radians = angle * Math.PI / 180;
        var textWidth = ctx.measureText(text).width;
        var x = centerX + textRadius * Math.cos(radians) - textWidth / 2;
        var y = centerY + textRadius * Math.sin(radians) + font_height / 3;
    
        ctx.fillText(text, x, y);
    }
    
    // Function to calculate distance from the center of a quadrant
    function calculateProximity(css, angle) {
      var quadrantX = Math.cos((angle + 90) * Math.PI / 180);
      var quadrantY = Math.sin((angle + 90) * Math.PI / 180);
      return Math.sqrt(Math.pow(css[1] - quadrantX, 2) + Math.pow(css[0] - quadrantY, 2));
    }

    // Define angles for each word
    var word_angles = {
      "Content": 15,
      "Relaxed": 45,
      "Calm": 75,
      "Tired": 105,
      "Sad": 135,
      "Depressed": 165,
      "Tense": 195,
      "Angry": 225,
      "Frustrated": 255,
      "Excited": 285,
      "Delighted": 315,
      "Happy": 345
    };


    // Place and scale each word based on proximity
    for (var word in word_angles) {
      var proximity = calculateProximity(css, word_angles[word]);
      var scale = 1 - proximity;
      scale = Math.max(0.3, scale);
      ctx.font = `${2 * font_height2 * scale}px Arial`
      placeText(word, word_angles[word]);
    }
    
    var proximity = Math.sqrt(Math.pow(css[1], 2) + Math.pow(css[0], 2));
    var scale = 1 - proximity;
    scale = Math.max(0.3, scale);
    ctx.font = `${2 * font_height2 * scale}px Arial`
    var x = centerX - ctx.measureText("Neutral").width / 2
    var y = centerY// - ctx.measureText("Neutral").height / 2
    ctx.fillText("Neutral", x, y);

  }

  network.listenJson('signals', function listener(data) {
    ctx.clearRect(0, 0, width, height)
    const { target_css, css, css_alpha } = data
    background(css)

    // if (target_css) {
    //   ctx.globalAlpha = 0.5
    //   ctx.strokeStyle = '#000'
    //   ctx.lineWidth = Math.max(2, width / 100)
    //   ctx.beginPath()
    //   ctx.arc(tox(target_css[0]), toy(target_css[1]), r * 1.4, 0, 2 * Math.PI)
    //   ctx.stroke()
    //   ctx.globalAlpha = 1
    // }
    if (css) {
      ctx.globalAlpha = 0.9
      ctx.fillStyle = '#000'
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = r / 4
      ctx.beginPath()
      ctx.arc(tox(css[0]), toy(css[1]), r, 0, 2 * Math.PI)
      ctx.fill()
      ctx.stroke();
    }
    if (!readonly && css_alpha) disp.alpha.value = css_alpha

    if (data.mode == 'one' && data.state_one && !hidestate) {
      const s = data.state_one
      disp.state.textContent = `one: ${s.state} (t=${Math.floor(s.timer)})`
    }

    if (data.mode == 'kosmos' && data.state_kosmos && !hidestate) {
      const s = data.state_kosmos
      const t1 = Math.floor(Math.max(0, data.state_kosmos.timer))
      const t2 = Math.floor(Math.max(0, data.state_kosmos.sonar_timer))
      const t3 = Math.floor(Math.max(0, data.state_kosmos.log_timer))
      let t = `${t1}`
      if (t2) t += `,s=${t2}`
      if (t3) t += `,l=${t3}`
      disp.state.textContent = `kosmos: ${s.state} (${t})`
    }
  })
}

export const ActionsButtons = ({name, values, network}) => {
  let value = null
  const els = h.div('cont').of(
    ui.hw(
      values.map(s => h.button(s).of(s))
    )
  ).els
  values.forEach(s => {
    els[s].addEventListener('click', () => {
      network.sender({action: `${name}=${s}`})
    })
  })
  network.listenJson('signals', data => {
    const v = data[name]
    if (v && v != value) {
      if (value && els[value]) {
        els[value].classList.remove('on')
      }
      if (els[v]) els[v].classList.add('on')
      value = v
    }
  })
  return els.cont
}

export const Actions = (output, {name, values, network}) => {
  h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of(name),
    ActionsButtons({name, values, network})
  ).into(output)
}

export const Transients = (output, {network, defs}) => {

  const limit = 100
  let include = [], exclude = [], paused = false
  const transients = defs.monitor_def.transients
  const disp = h.div().of(
    ui.h(
      'transients - filter:',
      h.input('include', {type: 'text'}), '\\',
      h.input('exclude', {type: 'text', value: 'heart'}),
      h.button('reset').of('reset'),
      h.button('clear').of('clear'),
      ui.toggle('pause').change(value => paused = value),
    ),
    h.div('.scrollable').of(h.div('output')),
  ).into(output).els

  update()

  const matches = s => (
    !include.length || include.some(token => s.search(token) >= 0)
  ) && (
    !exclude.length || exclude.every(token => s.search(token) == -1)
  )
  function update() {
    include = disp.include.value.split(/\s+/g).filter(x => x !== '')
    exclude = disp.exclude.value.split(/\s+/g).filter(x => x !== '')
    Array.from(disp.output.children).forEach(el => 
      el.classList[matches(el.textContent) ? 'remove' : 'add']('h'))
  }
  disp.include.addEventListener('change', update)
  disp.exclude.addEventListener('change', update)
  disp.reset.addEventListener('click', () => {
    disp.include.value = disp.exclude.value = ''
    include = exclude = []
    update()
  })
  disp.clear.addEventListener('click', () => {
    u.empty(disp.output)
  })

  const value_length = 30
  function listener(data) {
    if (paused) return
    let now = new Date().toTimeString().substr(0, 9)
    transients.forEach(transient => {
      if (data[transient] && data[transient].length !== 0) {
        let value = ('' + data[transient]).replace('\n', '\\n')
        if (value.length > value_length) value = value.substr(0, value_length - 3) + '...'
        const text = `${now} ${transient}: ${value}`
        const el = h.div().of(text).el
        if (!matches(text)) el.classList.add('h')
        disp.output.insertBefore(el, disp.output.firstChild)
        while (disp.output.children.length > limit) {
          disp.output.removeChild(disp.output.lastChild)
        }
      }
    })
  }

  network.listenJson('signals', listener)
}

export const ImageGPT = (output, {refresh_secs, headless, network}) => {
  refresh_secs = refresh_secs || .5
  let gptTextDiv = h.div({class: 'p'});
  const disp = h.div('cont').of(
    headless ? [] : h.div({class: 'header'}).of('vision'),
    h.div({style: 'height: 10px;'}),
    h.img('img'),
    h.div('.scrollable').of(h.div('output')),
  ).into(output).els
  disp.img.src = '/kinect'
  let id = window.setTimeout(refresh, 1e3 * refresh_secs)
  function refresh() {
    id = window.setTimeout(refresh, 1e3 * refresh_secs)
    disp.img.src = '/kinect?' + new Date().getTime();
  }
  
  function writeAnswerGPT(data) {
    if (headless && data && data.answer_gpt) {
      const el = h.div({class: 'answer-gpt-text'}).of(data.answer_gpt.split("]").pop()).el
      if (disp.output.children.length > 0) {
        disp.output.removeChild(disp.output.lastChild)
      }
      disp.output.insertBefore(el, disp.output.firstChild)
    }
  }

  if (headless) {
    network.listenJson('signals', writeAnswerGPT);
  }

  observe(disp.cont).start(() => {
    console.log('start')
    id = window.setTimeout(refresh, 1e3 * refresh_secs)
  }).stop(() => {
    console.log('stop')
    if (id) window.clearTimeout(id)
    id = null
  })
}

export const Image = (output, refresh_secs) => {
  refresh_secs = refresh_secs || .5
  const disp = h.div('cont').of(
    h.div({class: 'header'}).of('vision'),
    h.div({style: 'height: 10px;'}),
    h.img('img'),
  ).into(output).els
  disp.img.src = '/kinect'
  let id = window.setTimeout(refresh, 1e3 * refresh_secs)
  function refresh() {
    id = window.setTimeout(refresh, 1e3 * refresh_secs)
    disp.img.src = '/kinect?' + new Date().getTime()
  }
  observe(disp.cont).start(() => {
    console.log('start')
    id = window.setTimeout(refresh, 1e3 * refresh_secs)
  }).stop(() => {
    console.log('stop')
    if (id) window.clearTimeout(id)
    id = null
  })
}
