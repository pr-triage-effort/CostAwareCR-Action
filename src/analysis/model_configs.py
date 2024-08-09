from collections import OrderedDict
import numpy as np

weights = np.array([-7.79683165e+02,  2.26621931e+00, -7.84471571e+01,  5.81520163e+01,
        1.23670815e+02, -4.14351383e+00, -1.48440705e+01, -2.34363418e+01,
        5.20083768e+02,  3.71670608e+02,  2.94471431e+02, -9.50681141e+01,
        8.56416453e+00, -2.81553329e+00, -2.15266814e+01,  5.49428814e-01,
       -1.22172880e+01,  3.81968456e+01, -9.64557714e+02, -6.49508222e+02,
       -1.22547530e+02, -1.34826694e+01, -1.63876865e+02,  6.03916562e+01,
        3.08253938e+01, -3.84129017e+01, -4.94831871e+02,  2.10325794e+02,
       -1.22128332e+02,  9.50319986e+01,  3.08856469e+02,  1.33921387e+02,
       -9.47587103e+02, -1.88495825e+02, -5.17053457e+02,  1.17079186e+02])

#globals 
FEATURES = ['author_experience','author_merge_ratio', 'author_changes_per_week',
       'author_merge_ratio_in_project', 'total_change_num',
       'author_review_num', 'description_length', 'is_documentation',
       'is_bug_fixing', 'is_feature', 'project_changes_per_week',
       'project_merge_ratio', 'changes_per_author', 'num_of_reviewers',
       'num_of_bot_reviewers', 'avg_reviewer_experience',
       'avg_reviewer_review_count', 'lines_added', 'lines_deleted',
       'files_added', 'files_deleted', 'files_modified', 'num_of_directory',
       'modify_entropy', 'subsystem_num'
           ]
NUMERICAL_FEATURES = [
    'author_experience','author_merge_ratio', 'author_changes_per_week',
       'author_merge_ratio_in_project', 'total_change_num',
       'author_review_num', 'description_length', 'project_changes_per_week',
       'project_merge_ratio', 'changes_per_author', 'num_of_reviewers',
       'num_of_bot_reviewers', 'avg_reviewer_experience',
       'avg_reviewer_review_count', 'lines_added', 'lines_deleted',
       'files_added', 'files_deleted', 'files_modified', 'num_of_directory',
       'modify_entropy', 'subsystem_num'
]
BOOL_FEATURES = ['is_documentation', 'is_bug_fixing', 'is_feature']

rules = OrderedDict([
             ('rule_0_feature',
              'changes_per_author <= 1.7841873168945312 & num_of_reviewers <= -1.0535237491130829'),
             ('rule_1_feature',
              'author_merge_ratio_in_project > -0.28733599185943604 & author_merge_ratio > 0.1102062426507473 & changes_per_author > -0.8458887934684753'),
             ('rule_2_feature',
              'changes_per_author <= 1.8676908016204834 & avg_reviewer_review_count <= -0.8386645615100861'),
             ('rule_3_feature',
              'avg_reviewer_experience > -1.4394811987876892 & project_merge_ratio > 0.07264497131109238 & author_merge_ratio > 0.026092515792697668 & author_review_num > -0.6175498068332672'),
             ('rule_4_feature',
              'author_review_num > -0.6282753646373749 & num_of_reviewers > -1.0535237491130829 & avg_reviewer_review_count > -0.7467694580554962'),
             ('rule_5_feature',
              'author_merge_ratio <= 0.1102062426507473 & author_review_num > -0.6390009522438049 & avg_reviewer_review_count > -0.8218609094619751 & total_change_num > -0.7156917154788971'),
             ('rule_6_feature',
              'num_of_reviewers <= -1.0535237491130829 & author_merge_ratio <= 0.530774861574173'),
             ('rule_7_feature',
              'avg_reviewer_review_count > -0.7467694580554962 & num_of_reviewers > -1.0535237491130829 & author_review_num > -0.6175498068332672'),
             ('rule_8_feature',
              'avg_reviewer_review_count <= -0.7782763540744781 & author_review_num > -0.6390009522438049'),
             ('rule_9_feature',
              'project_changes_per_week > -0.830430656671524 & avg_reviewer_review_count <= 0.03239610604941845 & num_of_reviewers > -1.0535237491130829')])