import torch
import torch.nn as nn


def log_sum_exp(x):
    # See implementation detail in
    # http://timvieira.github.io/blog/post/2014/02/11/exp-normalize-trick/
    # b is a shift factor. see link.
    # x.size() = [N, C]:
    b, _ = torch.max(x, 1)
    # b.size() = [N, ], unsqueeze() required
    y = b + torch.log(torch.exp(x - b.unsqueeze(dim=1).expand_as(x)).sum(1))
    # y.size() = [N, ], no need to squeeze()
    return y

def class_select(logits, target):
    # in numpy, this would be logits[:, target].
    batch_size, num_classes = logits.size()
    if target.is_cuda:
        device = target.data.get_device()
        one_hot_mask = torch.autograd.Variable(torch.arange(0, num_classes)
                                               .long()
                                               .repeat(batch_size, 1)
                                               .cuda(device)
                                               .eq(target.data.repeat(num_classes, 1).t()))
    else:
        one_hot_mask = torch.autograd.Variable(torch.arange(0, num_classes)
                                               .long()
                                               .repeat(batch_size, 1)
                                               .eq(target.data.repeat(num_classes, 1).t()))
    return logits.masked_select(one_hot_mask)


def cross_entropy_with_weights(logits, target, weights=None):
    print(logits.shape, target.shape)
    
    assert logits.dim() == 2
    
    assert not target.requires_grad
    target = target.squeeze(1) if target.dim() == 2 else target
    assert target.dim() == 1

    loss = log_sum_exp(logits) - class_select(logits, target)
    if weights is not None:
        assert list(loss.size()) == list(weights.size())
        # Weight the loss
        loss = loss * weights
    return loss

class CrossEntropyLoss(nn.Module):
    """
    Cross entropy with instance-wise weights. Leave `aggregate` to None to obtain a loss
    vector of shape (batch_size,).
    """
    def __init__(self, aggregate='mean'):
        super(CrossEntropyLoss, self).__init__()
        assert aggregate in ['sum', 'mean', None]
        self.aggregate = aggregate

    def forward(self, logits, target, weights=None):
        if self.aggregate == 'sum':
            return cross_entropy_with_weights(logits, target, weights).sum()
        elif self.aggregate == 'mean':
            return cross_entropy_with_weights(logits, target, weights).mean()
        elif self.aggregate is None:
            return cross_entropy_with_weights(logits, target, weights)