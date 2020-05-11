#%% cluster deploy version!
import torch
from torch_net_utils import load_generator
from skimage.transform import resize
from imageio import imread
import matplotlib.pylab as plt
import numpy as np

G = load_generator("fc6")
G.requires_grad_(False)
G.cuda()
BGR_mean = torch.tensor([104.0, 117.0, 123.0])
BGR_mean = torch.reshape(BGR_mean, (1, 3, 1, 1))
#%%
import sys
sys.path.append(r"D:\Github\PerceptualSimilarity")
sys.path.append(r"E:\Github_Projects\PerceptualSimilarity")
import models  # from PerceptualSimilarity folder
# model = models.PerceptualLoss(model='net-lin', net='squeeze', use_gpu=1, gpu_ids=[0])
percept_vgg = models.PerceptualLoss(model='net-lin', net='vgg', use_gpu=1, gpu_ids=[0])
target_img = imread(r"E:\Monkey_Data\Generator_DB_Windows\nets\upconv\Cat.jpg")

#%%
def visualize(G, code, mode="cuda", percept_loss=True):
    """Do the De-caffe transform (Validated)
    works for a single code """
    if mode == "cpu":
        blobs = G(code)
    else:
        blobs = G(code.cuda())
    out_img = blobs['deconv0']  # get raw output image from GAN
    if mode == "cpu":
        clamp_out_img = torch.clamp(out_img + BGR_mean, 0, 255)
    else:
        clamp_out_img = torch.clamp(out_img + BGR_mean.cuda(), 0, 255)
    if percept_loss:  # tensor used to perform loss
        return clamp_out_img[:, [2, 1, 0], :, :] / (255 / 2) - 1
    else:
        vis_img = clamp_out_img[:, [2, 1, 0], :, :].permute([2, 3, 1, 0]).squeeze() / 255
        return vis_img

def L1loss(target, img):
    return (img - target).abs().sum(axis=2).mean()

def L2loss(target, img):
    return (img - target).pow(2).sum(axis=2).mean()
#%%
def img_backproj(target_img, lossfun=L1loss, nsteps=150, return_stat=True):
    tsr_target = target_img.astype(float)/255
    rsz_target = resize(tsr_target, (256, 256), anti_aliasing=True)
    tsr_target = torch.from_numpy(rsz_target).float().cuda()
    # assert size of this image is 256 256
    code = np.random.randn(4096)
    code = code.reshape(-1, 4096)
    feat = torch.from_numpy(code).float().requires_grad_(True)
    feat.cuda()
    optimizer = torch.optim.Adam([feat], lr=0.05, betas=(0.9, 0.999), eps=1e-08, weight_decay=0)
    loss_col = []
    norm_col = []
    for i in range(nsteps):
        optimizer.zero_grad()
        img = visualize(G, feat)
        #loss = (img - tsr_target).abs().sum(axis=2).mean() # This loss could be better? 
        loss = lossfun(img, tsr_target)
        loss.backward()
        optimizer.step()
        norm_col.append(feat.norm().detach().item())
        loss_col.append(loss.detach().item())
        # print("step%d" % i, loss)
    print("step%d" % i, loss.item())
    if return_stat:
        return feat.detach(), img.detach(), loss_col, norm_col
    else:
        return feat.detach(), img.detach()

def img_backproj_PL(target_img, lossfun=percept_loss, nsteps=150, return_stat=True):
    tsr_target = target_img.astype(float)/255
    rsz_target = resize(tsr_target, (256, 256), anti_aliasing=True)
    tsr_target = torch.from_numpy(rsz_target * 2.0 - 1).float().cuda()  # centered to be [-1, 1]
    tsr_target = tsr_target.unsqueeze(0).permute([0, 3, 1, 2])
    # assert size of this image is 256 256
    code = np.random.randn(4096)
    code = code.reshape(-1, 4096)
    feat = torch.from_numpy(code).float().requires_grad_(True)
    feat.cuda()
    optimizer = torch.optim.Adam([feat], lr=0.05, betas=(0.9, 0.999), eps=1e-08, weight_decay=0)
    loss_col = []
    norm_col = []
    for i in range(nsteps):
        optimizer.zero_grad()
        img = visualize(G, feat, percept_loss=True)
        #loss = (img - tsr_target).abs().sum(axis=2).mean() # This loss could be better?
        loss = lossfun(img, tsr_target)
        loss.backward()
        optimizer.step()
        norm_col.append(feat.norm().detach().item())
        loss_col.append(loss.detach().item())
        # print("step%d" % i, loss)
    print("step%d" % i, loss.item())
    img = visualize(G, feat, percept_loss=False)
    if return_stat:
        return feat.detach(), img.detach(), loss_col, norm_col
    else:
        return feat.detach(), img.detach()
#%%
from os.path import join
savedir = r"C:\Users\binxu\OneDrive - Washington University in St. Louis\PhotoRealism"
#%%
percept_net = models.PerceptualLoss(model='net-lin', net='vgg', use_gpu=1, gpu_ids=[0])
# def percept_loss(img, target, net=percept_net):
#     return net.forward(img.unsqueeze(0).permute([0, 3, 1, 2]), target.unsqueeze(0).permute([0, 3, 1, 2]))
#%%
nsteps = 500
percept_net = models.PerceptualLoss(model='net-lin', net='vgg', use_gpu=1, gpu_ids=[0])
zcode, fitimg, loss_col, norm_col = img_backproj_PL(target_img, percept_net.forward, nsteps=nsteps, return_stat=True)
label = "vggPLtr_step%d" % (nsteps)
plt.figure(figsize=[4, 4.5])
plt.imshow(fitimg.cpu().numpy())
plt.title(label)
plt.axis("off")
plt.savefig(join(savedir, "Embed_%s.jpg"%label))
plt.show()
plt.figure(figsize=[8, 8.5])
plt.subplot(2, 2, 1)
plt.imshow(fitimg.cpu().numpy())
plt.axis("off")
plt.subplot(2, 2, 2)
plt.imshow(target_img)
plt.axis("off")
plt.subplot(2, 2, 3)
plt.plot(loss_col)
plt.ylabel("Loss")
plt.xlabel("steps")
plt.subplot(2, 2, 4)
plt.plot(norm_col)
plt.ylabel("code norm")
plt.xlabel("steps")
plt.suptitle(label)
plt.savefig(join(savedir, "Embed_traj_%s.jpg"%label))
plt.show()
