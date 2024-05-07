from gaussian_splatting import *


def splat_test(H, W, u, cov2d, alpha, depth, color):
    import torch
    import simple_gaussian_reasterization as sgr
    u = torch.from_numpy(u).type(torch.float32).to('cuda')
    cov2d = torch.from_numpy(cov2d).type(torch.float32).to('cuda')
    alpha = torch.from_numpy(alpha).type(torch.float32).to('cuda')
    depth = torch.from_numpy(depth).type(torch.float32).to('cuda')
    color = torch.from_numpy(color).type(torch.float32).to('cuda')
    res = sgr.forward(H, W, u, cov2d, alpha, depth, color)

    # res_back = sgr.backward(H, W, u, cov2d, alpha, depth, color,
    #                    res[1], res[2], res[3], res[4], res[5], dloss_dgamma)
    image = torch.clone(res[0])
    contrib = torch.clone(res[1])
    final_tau = torch.clone(res[2])
    patch_offset_per_tile = torch.clone(res[3])
    gs_id_per_patch = torch.clone(res[4])
    cov2d_inv = torch.clone(res[5])
    dloss_dgammas = torch.ones([H, W, 3], dtype=torch.float32).to('cuda')
    print(image[:, 16, 16])

    res_back = sgr.backward(H, W, u, cov2d, alpha, depth, color,
                            contrib, final_tau, patch_offset_per_tile,
                            gs_id_per_patch, cov2d_inv, dloss_dgammas)

    res_cpu = []
    for r in res:
        res_cpu.append(r.to('cpu').numpy())
    res_cpu[0] = res_cpu[0].transpose(1, 2, 0)
    return res_cpu


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ply", help="the ply path")
    args = parser.parse_args()

    if args.ply:
        # ply_fn = "/home/liu/workspace/gaussian-splatting/output/test/point_cloud/iteration_30000/point_cloud.ply"
        ply_fn = args.ply
        print("Try to load %s ..." % ply_fn)
        gs = load_ply(ply_fn)
    else:
        print("not fly file.")
        # exit(0)
        # ply_fn = "/home/liu/workspace/gaussian-splatting/output/test/point_cloud/iteration_30000/point_cloud.ply"
        # gs = load_ply(ply_fn)

    gs_data = np.array([[0.,  0.,  0.,  # xyz
                        1.,  0.,  0., 0.,  # rot
                        0.5,  0.5,  0.5,  # size
                        1.,
                        1.772484,  -1.772484,  1.772484],
                        [1.,  0.,  0.,
                        1.,  0.,  0., 0.,
                        2,  0.5,  0.5,
                        1.,
                        1.772484,  -1.772484, -1.772484],
                        [0.,  1.,  0.,
                        1.,  0.,  0., 0.,
                        0.5,  2,  0.5,
                        1.,
                        -1.772484, 1.772484, -1.772484],
                        [0.,  0.,  1.,
                        1.,  0.,  0., 0.,
                        0.5,  0.5,  2,
                        1.,
                        -1.772484, -1.772484,  1.772484]
                        ], dtype=np.float32)

    dtypes = [('pos', '<f4', (3,)),
              ('rot', '<f4', (4,)),
              ('scale', '<f4', (3,)),
              ('alpha', '<f4'),
              ('sh', '<f4', (3,))]

    gs = np.frombuffer(gs_data.tobytes(), dtype=dtypes)

    # Camera info
    tcw = np.array([1.03796196, 0.42017467, 4.67804612])
    Rcw = np.array([[0.89699204,  0.06525223,  0.43720409],
                    [-0.04508268,  0.99739184, -0.05636552],
                    [-0.43974177,  0.03084909,  0.89759429]]).T

    # W = int(979)  # 1957  # 979
    # H = int(546)  # 1091  # 546
    # focal_x = 1163.2547280302354/2.
    # focal_y = 1156.280404988286/2.

    W = int(32)  # 1957  # 979
    H = int(32)  # 1091  # 546
    focal_x = 16
    focal_y = 16

    K = np.array([[focal_x, 0, W/2.],
                  [0, focal_y, H/2.],
                  [0, 0, 1.]])

    Tcw = np.eye(4)
    Tcw[:3, :3] = Rcw
    Tcw[:3, 3] = tcw
    cam_center = np.linalg.inv(Tcw)[:3, 3]

    pw = gs['pos']

    # step1. Transform pw to camera frame,
    # and project it to iamge.
    u, pc = project(pw, Tcw, K)

    depth = pc[:, 2]

    # step2. Calcuate the 3d Gaussian.
    cov3d = compute_cov_3d(gs['scale'], gs['rot'])

    # step3. Project the 3D Gaussian to 2d image as a 2d Gaussian.
    cov2d = compute_cov_2d(pc, focal_x, focal_y, cov3d, Rcw)

    # step4. get color info
    ray_dir = pw[:, :3] - cam_center
    ray_dir /= np.linalg.norm(ray_dir, axis=1)[:, np.newaxis]
    color = sh2color(gs['sh'], ray_dir)

    # step5. Blend the 2d Gaussian to image
    res = splat_test(H, W, u, cov2d, gs['alpha'], depth, color)
    print(res[3])

    plt.imshow(res[0])

    plt.show()
