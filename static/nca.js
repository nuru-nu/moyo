import { h, u, ui, observe } from './smanmi/util.js'
import { CA } from './ca.js';

export const NcaView = (output, {network, height}) => {
  const els = h.div().of(
    h.div({style: 'text-align:center'}).of(
      h.a('a', {target: '_blank', href: '#'}).of(
        h.img('img', {src: 'black.png', height, width: height}),
      ),
      h.canvas('canvas', {height, width: height * 3})
    )
  ).into(output).els

  const gl = els.canvas.getContext("webgl")
  let ca = new CA(gl, models, [32*3, 32])
  ca.alignment = 0

  let running = false
  function render() {
    ca.step()
    twgl.bindFramebufferInfo(gl);
    ca.draw()
    if (running) {
      requestAnimationFrame(render)
    }
  }
  // ca.paint(0, 0, 1000, 0)

  let nca = null
  network.listenJson('signals', data => {
    if (data.animation === 'nca' || data.animation === 'nca2') {
      if (nca != data[data.animation]) {
        nca = data[data.animation]
        if (nca) {
          const [group, _] = nca.split('_')
          els.a.href = `https://www.robots.ox.ac.uk/~vgg/data/dtd/thumbs/${group}/${nca}.jpg`
          els.img.src = `https://www.robots.ox.ac.uk/~vgg/data/dtd/thumbs/${group}/${nca}.jpg`
          fetch(`/nca_data?name=${nca}`).then(resp => resp.json()).then(models => {
            ca.setWeights(models)
            if (!running) {
              running = true
              requestAnimationFrame(render)
            }
          })
        } else {
          els.a.href = '#'
          els.img.src = 'black.png'
          running = false
        }
      }
    }
  })
}

const models = {"model_names": ["blotchy_0084"], "layers": [{"scale": 1.377746343612671, "data": "data:image/PNG;base64,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", "shape": [49, 96], "quant_scale_zero": [2.0, 0.0], "layout": [1, 1]}, {"scale": 0.5080177187919617, "data": "data:image/PNG;base64,iVBORw0KGgoAAAANSUhEUgAAAAMAAABhCAYAAAATFBvuAAAE6ElEQVR4nAXBfVCTdRwA8O23714Y7BkwGWNjc0McbENQQARBcx7IWwqKl1fmCx2aXi/nZV39ocel51V31Wl6V9pZp3WV5QlymQNEgZI3BwMHbI4B29jG3hjs/fVhfT7Eb+9e/1KlGPfme446IaTv7pJWwVZa1mMSmjRvOCwZ5SSC/ZCN5G31iSuBTaceKYrdMGt2dexdta+f/Xrci9ja6UN2sNg7umSTyKfxWfnHy63ueelpVFHb/GfEZJzZ1jrOh2Xrw7aw1p4+or7xLiymNHmFrId6CuXqEcjij+6zGeoj7tKwCrBX8899MwbK4PJHryCxIrJO0VaiLX9Eoujm5CNjdryW4sg+mIbOy04eODerXZBevFAI6g/DJFK49ID1zv01WPgxQ6fjjpCTy8rXUD2LG8wJiJTMcH8lsaCltmm3eUnWWFumQCflFfmnCq4KH5YkfYAiAmqrIqYRk7Q+DVg0pFaVuafwHOGyFbZg2zxssZoIh3r2A3Fg5sSsBrnSH7N/B1mtwDbH8GcsFVkuIdXq+JhGPBwMdAkuo1lnTj7fiflZcWISZKU5edbROlawycEEflpwFKPkNqAfNnBRv5bQeg+u5Ebe5w2ClCt5AJg5JmC17wK30SJ4sZxgHfFs7UYZuHv0diDTNb1TGQJndO21X1jbKMvKUD0il+ThA1gvndQjNSDfkKn0qKiInahOpcNuPu23J7gjWAPWBjAVMKu5zyhUFydzHvX1jy3N0qlxXgHCUIOgqY/fZVyMXss0wtKrpyfCBxfx5Tj9P9jEFndYpM2CEY/tLHiFRVWu7hm6hJM1heyR3jBavjWRaoFuyGI+CYR3Vab4z0y0I51K7hnVxGyUn/xPkSwmSmk53pitJ/MrIMpVef95TuGW4TtGUHePhZlMloqHYbAM7Xq9pVQT0jPgMUcJdF5Q24BLeClyjxD5Jm5Q3LbppYxCQgi8xAvaZJNdcjuQvRUyJLp/U1cjK1+x033E93bLLhHyBZOsqvQAmEurmEJ3rNw+V+BGLfL6IW86MyDnM2MwMNC5kcrwuO4nifxIZgy8XbdYSabHX5YgZ1qSOpriF6t1tAm0dpgzcY2PNIdM2/MQs2+977MZRoJZtOgEKsb75KbP6y7BolGADWud6R2GCN3AwxGp2/fW3cqijUF5nArBzWHFeVpEyHF7WSh3b3V2zgKVOGWpSYBJias4DNXaftFwA3g1P0sWmFXlrLHgr1DT2OYgD2uW2PHcYujVTRSuBVccrhKbBpUTfHo2MTSPXS9hIj8736kgv6Tz8pPMsDq0evGq7dP0Rbn6G+Btdn8+GAjuMH7RrIX742O01Gq+RyC7yYfy4o2sKQVOtxPeIIFhnt6YJEmOMNh/z0Px9p2n9TafgFpHeROixhWM5I9VSP6aMyCDzH8tkvAT7mlTGBDo1b7gVRzGqeL4dljfL/LVdE6FSFG+DoQKb+DBpp15hvh0HUwzWPkpK+Mi4Wbnd2gPQWiLS5KHdIvrTTCNee6QBxz4nkaHElE5me/MJaIfj7Qfs0OOmxYwgRSvOms7glYdyi4sNNkVC7ujEMWwqva6fTmmoP8paJQK3GqU9tGaYzjUt9QEb6mH8mKdxyLInLbC5pLbQuQy/RbAg3yucfJ7hsjwVSfKUI9OhusaXHhe2xnUTc4r4mvN6wGx/Nn/euZZq9ugmSwAAAAASUVORK5CYII=", "shape": [97, 12], "quant_scale_zero": [4.0, 0.4980392156862745], "layout": [1, 1]}]};