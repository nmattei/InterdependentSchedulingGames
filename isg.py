'''
  File:   isg.py
  Author: Nicholas Mattei (nicholas.mattei@nicta.com.au)
  Date: 25 Jan 2016

  * Copyright (c) 2014/2015/2016, Nicholas Mattei and Data61/NICTA
  * All rights reserved.
  *
  * Developed by: Nicholas Mattei
  *               Data61 / NICTA
  *               http://www.nickmattei.net
  *               http://www.preflib.org
  *
  * Redistribution and use in source and binary forms, with or without
  * modification, are permitted provided that the following conditions are met:
  *     * Redistributions of source code must retain the above copyright
  *       notice, this list of conditions and the following disclaimer.
  *     * Redistributions in binary form must reproduce the above copyright
  *       notice, this list of conditions and the following disclaimer in the
  *       documentation and/or other materials provided with the distribution.
  *     * Neither the name of NICTA nor the
  *       names of its contributors may be used to endorse or promote products
  *       derived from this software without specific prior written permission.
  *
  * THIS SOFTWARE IS PROVIDED BY NICTA ''AS IS'' AND ANY
  * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
  * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
  * DISCLAIMED. IN NO EVENT SHALL NICTA BE LIABLE FOR ANY
  * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
  * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
  * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
  * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
  * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
  * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

About
--------------------
  MIP implementation of the schedualing games devloped in our paper.
  This is my first MIP so I make no claims of optimality or quality.

'''

from gurobipy import *
import itertools
import random
import copy
import pickle


# Try adding the schedule constraint and runnign again...
# For each player,

'''
  To get all solutions we would need to add a constraint that says we have
  as much utility but that we don't have the active times mentioned here.
  I think we can do that pretty easily...

  We can then take the set of solutions and feed them to another LP to see
  if they are in PNE.  Not sure how hard this would be.

'''

def gen_instance(num_players, num_tasks, uniform=False):
  '''
  Generate an instance of an ISG with num_players and num_tasks

  Parameters
  -----------
  num_players: Integer
    Number of players.
  num_tasks: Integer
    Number of tasks

  Returns
  -----------
    time_steps: list
      A list of labels for the time steps.  Makes life easier.

    tasks: Dictionary
      A dictionary of player --> tasks where tasks is a list of tasks
      for the player key.

      e.g.,
      tasks = { 'a' : ['Ta1', 'Ta2', 'Ta3', 'Ta4'],
                'b' : ['Tb1', 'Tb2', 'Tb3', 'Tb4']
              }

      rewards: Dictionary
        A dict from every task present in tasks to an integer or
        real valued reward. e.g.
          rewards = { 'Ta1' : 10,
                      'Ta2' : 20,
                      'Ta3' : 30
                    }

      edges: list of tuple
        Precidence constraints.  (e,v) implies that e --> v or
        that e must preceede v... that e enables the service to commence
        on v.  e.g.
          edges = [
               ('Ta1', 'Ta2'),
               ('Tb2', 'Tb4')
             ]
  Notes
  -----------

  '''

  # Generate time steps with naming convention ts_x
  time_steps = ['ts_'+str(i) for i in range(1, num_tasks+1)]

  # Generate tasks with naming convention Px_Ty.
  tasks = {}
  for i in range(1, num_players+1):
    t = ["P"+str(i)+"_T"+str(j) for j in range(1,num_tasks+1)]
    tasks["P"+str(i)] = t

  all_tasks = list(itertools.chain.from_iterable(list(tasks.values())))

  # Generate the rewards.
  rewards = {}
  for i in all_tasks:
    if not uniform:
      rewards[i] = random.randint(50,100)
    else:
      rewards[i] = 1

  # # Permute the edges randomly.. then p0 --> p1 with 50% chance. for
  # # all pairs...
  # edges = []
  # pop_list = copy.copy(all_tasks)
  # random.shuffle(pop_list)
  # while len(pop_list) > 1:
  #   t0 = pop_list.pop()
  #   if random.randint(0,1) == 1:
  #     edges.append((t0, pop_list[0]))

  # Permute the Edges Randomly then for r randomly in 1...R,
  # Generate p ---> p+r with probability 0.50 each.
  edges = []
  pop_list = copy.copy(all_tasks)
  random.shuffle(pop_list)

  # print(pop_list)
  while len(pop_list) > 1:
    t0 = pop_list.pop(0)
    # d = str(t0)
    for r in range(random.randint(1, 5)):
      if len(pop_list) > r+1:
        if random.randint(0,3) > 1:
          edges.append((t0, pop_list[r]))
          # d += " --> " + str(pop_list[r])
    # print(d)

  return time_steps, tasks, rewards, edges


def model_isg(time_steps, tasks, rewards, edges):
  '''
  Generate a model of the ISG with the given task set,
  rewards, and edges between tasks.

  Parameters
  -----------
    time_steps: list
      A list of labels for the time steps.  Makes life easier.

    tasks: Dictionary
      A dictionary of player --> tasks where tasks is a list of tasks
      for the player key.

      e.g.,
      tasks = { 'a' : ['Ta1', 'Ta2', 'Ta3', 'Ta4'],
                'b' : ['Tb1', 'Tb2', 'Tb3', 'Tb4']
              }

      rewards: Dictionary
        A dict from every task present in tasks to an integer or
        real valued reward. e.g.
          rewards = { 'Ta1' : 10,
                      'Ta2' : 20,
                      'Ta3' : 30
                    }

      edges: list of tuple
        Precidence constraints.  (e,v) implies that e --> v or
        that e must preceede v... that e enables the service to commence
        on v.  e.g.
          edges = [
               ('Ta1', 'Ta2'),
               ('Tb2', 'Tb4')
             ]

  Returns
  -----------
    model: Gurobi Model
      A MIP model of the ISG game with the given parameters.

  Notes
  -----------

  '''
  m = Model('ISG')

  scheduled_times = {}
  active_times = {}
  # Make variables for all scheduled times and active times for all tasks.
  all_tasks = list(itertools.chain.from_iterable(list(tasks.values())))

  for v,t in itertools.product(all_tasks, time_steps):
    scheduled_times[v,t] = m.addVar(vtype=GRB.BINARY, name='s_%s_%s' % (v, t))
    active_times[v,t] = m.addVar(vtype=GRB.BINARY, name='a_%s_%s' % (v, t))

  m.update()

  # Every task is only scheduled once.
  for v in all_tasks:
    m.addConstr(quicksum(scheduled_times[v,t] for t in time_steps) == 1, 'st_%s%s' % (v,t))

  # For the set of each player's tasks, there is only one task per time step.
  for p,pt in tasks.items():
    for t in time_steps:
      m.addConstr(quicksum(scheduled_times[v,t] for v in pt) == 1, 'pl_%s_at_time_%s' % (p,t))

  # Link active times to scheduled times.
  for v in all_tasks:
    for i,t in enumerate(time_steps):
      m.addConstr(quicksum(scheduled_times[v, time_steps[j]] for j in range(i+1)) >= active_times[v,t], 'act_time%s%s' % (v,t))

  # Obey Edge Constraints...
  for e in edges:
    for t in time_steps:
      m.addConstr(active_times[e[1], t] <= active_times[e[0],t], 'edge_%s_to_%s_%s' % (e[0], e[1], t))

  # Set The model Objective...
  m.setObjective(quicksum(active_times[v,t] * rewards[v] for v,t in itertools.product(all_tasks, time_steps)), GRB.MAXIMIZE)

  m.update()
  return m, scheduled_times


def pretty_print_solution(m, time_steps, tasks, scheduled_times):
  '''
  Pretty print the solution.

  Parameters
  -----------
    m: gurobi model

    time_steps: list
      A list of labels for the time steps.  Makes life easier.

  Returns
  -----------
    nothing.

  Notes
  -----------

  '''
  if m.status == GRB.Status.OPTIMAL:

    print("Finished in (seconds): " + str(m.Runtime))
    print("Schedule Utility: " + str(m.ObjVal))

    solution = m.getAttr('x', scheduled_times)
    # Pretty Print...
    print("\t\t" + "\t".join(time_steps))
    for p in sorted(tasks.keys()):
      outstr = "Player: " + str(p) + "\t"
      for t in time_steps:
        for ct in tasks[p]:
          if solution[ct,t] == 1.0:
            outstr += ct + "\t"
      print(outstr)
  else:
    print("No Solution")


if __name__ == "__main__":
  results = {}
  uniform_results = {}
  range_num_players = [2, 5, 10]
  range_num_tasks = [5, 10, 30, 50, 70, 100]
  samples = 100
  for p,t in itertools.product(range_num_players, range_num_tasks):
    print("On: " + str(p) + " players and " + str(t) + " tasks.")
    for s in range(samples):
      time_steps, tasks, rewards, edges = gen_instance(p, t)
      model, scheduled_times = model_isg(time_steps, tasks, rewards, edges)
      # Quiet down the Optimizer...
      model.setParam( 'OutputFlag', False )
      model.optimize()
      # pretty_print_solution(model, time_steps, tasks, scheduled_times)
      # print(model.Runtime)
      results[(p,t)] = results.get((p,t), []) + [model.Runtime]

      time_steps, tasks, rewards, edges = gen_instance(p, t, uniform=True)
      model, scheduled_times = model_isg(time_steps, tasks, rewards, edges)
      # Quiet down the Optimizer...
      model.setParam( 'OutputFlag', False )
      model.optimize()
      # pretty_print_solution(model, time_steps, tasks, scheduled_times)
      # print(model.Runtime)
      uniform_results[(p,t)] = uniform_results.get((p,t), []) + [model.Runtime]

  with open("./stepping_run.pickle", 'wb') as output_file:
    pickle.dump(results, output_file)
  with open("./stepping_run_uniform.pickle", 'wb') as output_file:
    pickle.dump(uniform_results, output_file)





