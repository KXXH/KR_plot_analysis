import Vue from 'vue'
import Router from 'vue-router'
import HelloWorld from '@/components/HelloWorld'
import ActorPlot from '@/components/ActorPlot'


Vue.use(Router)

export default new Router({
  routes: [
    {
      path: '/',
      name: 'HelloWorld',
      component: HelloWorld
    },
    {
      path: '/actor',
      name: 'ActorPlot',
      component: ActorPlot
    }
  ]
})


