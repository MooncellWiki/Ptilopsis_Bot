from utils.job import Job

import copy

def format_time(time):
    return '{}分{:.1f}秒'.format(int(time / 60), time % 60)


def parse_checkpoint(checkpoint):
    if checkpoint['randomizeReachOffset'] == True:
        print('randomizeReachOffset = True')
    if checkpoint['reachDistance'] != 0.0:
        print('reachDistance =', checkpoint['reachDistance'])

    if checkpoint['reachOffset']['x'] == 0.0:
        x_pos = '{}'.format(checkpoint['position']['col'])
    else:
        x_pos = '{}'.format(checkpoint['position']['col'] + checkpoint['reachOffset']['x'])
    if checkpoint['reachOffset']['y'] == 0.0:
        y_pos = '{}'.format(checkpoint['position']['row'])
    else:
        y_pos = '{}'.format(checkpoint['position']['row'] + checkpoint['reachOffset']['y'])
    text = parse_checkPointType(checkpoint['type'], checkpoint['time'], x_pos, y_pos)
    return text


def parse_route(route):
    if not route:
        return None
    route_result = ''
    start_x = '{}'.format(route['startPosition']['col'])
    if route['spawnRandomRange']['x'] != 0.0:
        start_x += '±{}'.format(route['spawnRandomRange']['x'])
    if route['spawnOffset']['x'] != 0.0:
        start_x += '+{}'.format(route['spawnOffset']['x'])
    start_y = '{}'.format(route['startPosition']['row'])
    if route['spawnRandomRange']['y'] != 0.0:
        start_y += '±{}'.format(route['spawnRandomRange']['y'])
    if route['spawnOffset']['y'] != 0.0:
        start_y += '+{}'.format(route['spawnOffset']['y'])
    route_result += '({}, {})'.format(start_x, start_y)
    for checkpoint in route['checkpoints']:
        route_result += parse_checkpoint(checkpoint)
    route_result += '→({}, {})'.format(route['endPosition']['col'], route['endPosition']['row'])
    return route_result


def parse_motionMode(motionMode):
    try:
        return {
            0: 'WALK',
            1: 'FLY',
        }[motionMode]
    except:
        # print('Unexpected motionMode {}.'.format(motionMode))
        # return 'E_NUM' if motionMode == 2 else 'UNKNOWN'
        print('Unexpected motionMode.')
        return 'E_NUM'


def parse_actionType(action_count, key, actionType):
    if actionType == 0:
        pass
    elif actionType == 1:
        print('No.{} {} actionType: {}'.format(action_count, key, 'PREVIEW_CURSOR'))
    elif actionType == 2:
        print('No.{} {} actionType: {}'.format(action_count, key, 'STORY'))
    elif actionType == 3:
        print('No.{} {} actionType: {}'.format(action_count, key, 'TUTORIAL'))
    elif actionType == 4:
        print('No.{} {} actionType: {}'.format(action_count, key, 'PLAY_BGM'))
    elif actionType == 5:
        print('No.{} {} actionType: {}'.format(action_count, key, 'DISPLAY_ENEMY_INFO'))
    elif actionType == 6:
        print('No.{} {} actionType: {}'.format(action_count, key, 'ACTIVATE_PREDEFINED'))
    elif actionType == 7:
        print('No.{} {} actionType: {}'.format(action_count, key, 'E_NUM'))
    else:
        print('No.{} {} actionType: {}'.format(action_count, key, 'UNKNOWN'))


def parse_checkPointType(checkpoint_type, time, x, y):
    try:
        return {
            0: '→({}, {})'.format(x, y),
            1: '(WAIT: {}s)'.format(time),
            2: '(WAIT_PLAY: {}s)'.format(time),
            3: '(WAIT_FRAGMENT: {}s)'.format(time),
            4: '(WAIT_WAVE: {}s)'.format(time),
            5: '→通道',
            6: '→({}, {})'.format(x, y)
        }[checkpoint_type]
    except:
        return '(UNKNOWN)'


def get_routes(level_routes):
    return [parse_route(route) for route in level_routes]
    # route_id = -1
    # for route in level_routes:
    #     route_id += 1
    #     if route == None:
    #         continue
    #     print('%d: ' % route_id)
    #     print('motionMode:', parse_motionMode(route['motionMode']))
    #     if route['allowDiagonalMove'] == False:
    #         print('ADM = False')
    #     if route['visitEveryTileCenter'] == True:
    #         print('VETC = True')
    #     if route['visitEveryNodeCenter'] == True:
    #         print('VENC = True')
    #     print(parse_route(route))


def get_waves(level_waves):
    wave_count = -1
    min_time = 0.0
    spawn_group = {}
    for wave in level_waves:
        wave_count += 1
        # print('wave {} name: {}'.format(wave_count, wave['name']))
        min_time += wave['preDelay']
        fragment_count = -1
        for fragment in wave['fragments']:
            fragment_count += 1
            # print('fragment {} name: {}'.format(fragment_count, fragment['name']))
            min_time += fragment['preDelay']
            # min_time += max([action['preDelay'] + (action['count']-1) * action['interval'] + int(action['autoPreviewRoute'])*1.5 for action in fragment['actions']])
            min_time += max(
                [action['preDelay'] + (action['count'] - 1) * action['interval'] for action in fragment['actions']])
            action_count = -1
            for action in fragment['actions']:
                if action['actionType'] != 0:
                    continue
                action_count += 1
                # parse_actionType(action_count, action['key'], action['actionType'])
                # if action['managedByScheduler'] == False:
                #     print('No.{} {} managedByScheduler = False.'.format(action_count, action['key']))
                # if action['blockFragment'] == True:
                #     print('No.{} {} blockFragment = True.'.format(action_count, action['key']))
                # if action['autoPreviewRoute'] == False:
                #     print('No.{} {} autoPreviewRoute = False.'.format(action_count, action['key']))
                # if action['isUnharmfulAndAlwaysCountAsKilled'] == True:
                #     print('No.{} {} isUnharmfulAndAlwaysCountAsKilled = True.'.format(action_count, action['key']))
                # if 'hiddenGroup' in action and action['hiddenGroup'] != None:
                #     print('No.{} {} hiddenGroup = {}.'.format(action_count, action['key'], action['hiddenGroup']))
                # if action['actionType'] != 0 and 'randomSpawnGroupKey' in action and action['randomSpawnGroupKey'] != None:
                #     if action['weight'] - action['weightValue'] != 0.0:
                #     print('No.{} {} group = {}, weight = {}, num = {}.'.format(action_count, action['key'], action['randomSpawnGroupKey'], action['weight'], action['count']))
            # min_time += 0.3
        min_time += wave['postDelay']
        # min_time += 0.5
    print(format_time(min_time))


def count_enemy(level_waves):
    e_num = 0
    e_low = 0
    e_high = 0
    wave_count = -1
    min_time = 0.0
    min_time_low = 0.0
    min_time_high = 0.0
    for wave in level_waves:
        wave_count += 1
        min_time += wave['preDelay']
        min_time_low += wave['preDelay']
        min_time_high += wave['preDelay']
        fragment_count = -1
        for fragment in wave['fragments']:
            fragment_count += 1
            min_time += fragment['preDelay']
            min_time_low += fragment['preDelay']
            min_time_high += fragment['preDelay']
            temp1 = [action['preDelay'] + (action['count'] - 1) * action['interval'] for action in fragment['actions']]
            temp2_1 = [action['preDelay'] + (action['count'] - 1) * action['interval'] for action in fragment['actions'] if 'randomSpawnGroupKey' not in action or action['randomSpawnGroupKey'] == None]
            temp2_2 = copy.deepcopy(temp2_1)
            min_time += max(temp1)

            spawn_groups = {}
            for action in fragment['actions']:
                if action['actionType'] == 0:
                    if 'randomSpawnGroupKey' in action and action['randomSpawnGroupKey'] != None:
                        if action['randomSpawnGroupKey'] not in spawn_groups:
                            spawn_groups[action['randomSpawnGroupKey']] = []
                        spawn_groups[action['randomSpawnGroupKey']].append(action)
                    else:
                        e_num += action['count']
            for s_group in spawn_groups:
                e_low += min([a['count'] if a['key'] != '' else 0 for a in spawn_groups[s_group]])
                e_high += max([a['count'] if a['key'] != '' else 0 for a in spawn_groups[s_group]])
                temp2_1.append(min([a['preDelay'] + (a['count'] - 1) * a['interval'] for a in spawn_groups[s_group]]))
                temp2_2.append(max([a['preDelay'] + (a['count'] - 1) * a['interval'] for a in spawn_groups[s_group]]))

            if temp2_1 != []:
                min_time_low += max(temp2_1)
            if temp2_2 != []:
                min_time_high += max(temp2_2)

        min_time += wave['postDelay']
        min_time_low += wave['postDelay']
    if e_low + e_num != e_high + e_num:
        print('num: {}~{}'.format(e_low + e_num, e_high + e_num))
    else:
        print('num: {}'.format(e_low + e_num))
    if min_time_low != min_time_high:
        print('time: {}~{}'.format(format_time(min_time_low), format_time(min_time_high)))
    else:
        print('time: {}'.format(format_time(min_time_low)))


def get_waves_table(level_waves, routes, enemy_table):
    wave_table = '{|class="wikitable sortable" style="text-align:center; width:800px; display:table; white-space:normal;"\n!No.!!头像!!名字!!总时间!!当前波次时间'
    total_time = 0.0
    enemy_dict = []
    for wave in level_waves:
        wave_time = wave['preDelay']
        total_time += wave['preDelay']
        for fragment in wave['fragments']:
            wave_time += fragment['preDelay']
            total_time += fragment['preDelay']
            for action in fragment['actions']:
                if action['actionType'] != 0:
                    continue
                for action_count in range(action['count']):
                    if action['key'] not in enemy_table:
                        name = '未知'
                    else:
                        name = enemy_table[action['key']]['name']
                    enemy_dict.append({
                        'time_w': wave_time + action['preDelay'] + action_count * action['interval'],
                        'time_t': total_time + action['preDelay'] + action_count * action['interval'],
                        'name': name,
                        'route': routes[action['routeIndex']]
                    })
            wave_time += max(
                [action['preDelay'] + (action['count'] - 1) * action['interval'] for action in fragment['actions']])
            total_time += max(
                [action['preDelay'] + (action['count'] - 1) * action['interval'] for action in fragment['actions']])
        total_time += wave['postDelay']

    sorted_enemy = sorted(enemy_dict, key = lambda x: x['time_t'])

    count = 0
    for enemy in sorted_enemy:
        count += 1
        wave_table += '\n|-\n|{}\n|{{{{敌人头像|{}|px=50}}}}\n|{}\n|{}\n|{}'.format(count, enemy['name'], enemy['name'],
            format_time(enemy['time_t']), format_time(enemy['time_w']))
        wave_table += '\n|- class="expand-child" style="font-size:85%; line-height:1.2; color:gray;"\n|colspan="5"|{}'.format(
            enemy['route'])
    wave_table += '\n|}'

    return wave_table


class Route(Job):
    def _run(self):
        enemy_table = self.getgd('excel/enemy_handbook_table.json')
        stage_table = self.getgd('excel/stage_table.json')
        enemy_db = self.getgd('levels/enemydata/enemy_database.json')

        # levelId = 'Obt/Campaign/level_camp_03'  # 市区
        levelId = 'Obt/Campaign/level_camp_r_03'

        level_table = self.getgd('levels/' + levelId + '.json')
        routes = get_routes(level_table['routes'])
        get_waves(level_table['waves'])
        wave_table = get_waves_table(level_table['waves'], routes, enemy_table)

        # for stage in stage_table['stages']:
        #     levelId = stage_table['stages'][stage]['levelId']
        #     if levelId != None and stage_table['stages'][stage]['difficulty'] != 'FOUR_STAR':
        #         print('==={} {}==='.format(stage_table['stages'][stage]['code'], stage_table['stages'][stage]['name']))
        #         level_table = self.getgd('levels/' + levelId + '.json')
        #         get_waves(level_table['waves'])
        #         routes = get_routes(level_table['routes'])
        #         wave_table = get_waves_table(level_table['waves'], routes, enemy_table)

        # roguelike_table = self.getgd('excel/roguelike_table.json')
        # for stage in roguelike_table['stages']:
        #     levelId = roguelike_table['stages'][stage]['levelId']
        #     if levelId != None and roguelike_table['stages'][stage]['difficulty'] != 'FOUR_STAR':
        #         print('==={} {}==='.format(roguelike_table['stages'][stage]['code'], roguelike_table['stages'][stage]['name']))
        #         level_table = self.getgd('levels/' + levelId + '.json')
        #         count_enemy(level_table['waves'])

        self.wiki.edit(
            title = '用户:Seniorious/route',
            text = wave_table,
            summary = 'update'
        )
        # print(wave_table)
        print('Updated: {}.'.format('用户:Seniorious/route'))
