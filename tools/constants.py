import os

module_path = os.path.split(__file__)[0]
inputs_path = os.path.join(module_path, 'inputs')
dcm_report_path = os.path.join(inputs_path, 'dcm_reports')
prog_report_path = os.path.join(inputs_path, 'programmatic_reports')
plan_path = os.path.join(inputs_path, 'plans')
final_report_path = os.path.join(module_path, 'final_reports')


def create_paths():
    for path in [dcm_report_path, prog_report_path, plan_path, final_report_path]:
        if not os.path.isdir(path):
            os.makedirs(path)


if __name__ == '__main__':
    create_paths()
